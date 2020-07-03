from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import IntegrityError
import datetime
import logging
logging.basicConfig()
def lazy_load(obj):
    """
    Helper method to call all attribs on an obj to load them before detaching from the session
    """
    [getattr(obj, method) for method in dir(obj) if callable(getattr(obj, method))]

Base = declarative_base()

class LockEnum(Enum):
    read = 1
    write = 2

class ResourceLock(Base):
    """Class respresenting a lock obtained by a client on a particular resource. Locks can include read or write.

    Attributes:
    resource_lock_id -- ID for the lock (given to the calling code for release)
    lock_type        -- read or write
    created          -- time at which lock was obtained
    client           -- Client holding the lock
    resource         -- Resource being locked
    """
    __tablename__ = 'resource_lock'

    resource_lock_id = Column(Integer, primary_key=True)
    lock_type = Column(String(5), nullable=False)
    created = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    client_id = Column(Integer, ForeignKey("client.client_id"))
    client = relationship("Client")
    resource_id = Column(Integer, ForeignKey("resource.resource_id"))
    resource = relationship("Resource")

    def __repr__(self):
        return "<ResourceLock(resource_lock_id={}, lock_type='{}', client='{}', resource='{}')>".format(self.resource_lock_id, self.lock_type, self.client.name, self.resource.uri)

    def to_dict(self):
        return {"resource_lock_id": self.resource_lock_id, "client":self.client.to_dict(), "resource":self.resource.to_dict(), "lock_type":self.lock_type, "created":self.created}

class Resource(Base):
    """Class respresenting an abstract resource like a database or a file

    Attributes:
    resource_id -- internal ID for the resource
    uri         -- unique string representation of the resource e.g. database URI, path to file
    """
    __tablename__ = 'resource'

    resource_id = Column(Integer, primary_key=True)
    uri = Column(String(512), nullable=False, unique=True)

    def __repr__(self):
        return "<Resource(resource_id={}, uri='{}')>".format(
            self.resource_id, self.uri)

    def to_dict(self):
        return {"resource_id": self.resource_id, "uri":self.uri}


class Client(Base):
    """Class respresenting an abstract client who needs access to a resource.
    A client might be a process, application or Real Person[tm]

    Attributes:
    client_id -- internal ID for the client
    name      -- unique string name for client. Could be the name of an application, or an email address for a person
    """

    __tablename__ = 'client'

    client_id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, unique=True)

    def __repr__(self):
        return "<Client(client_id={}, name='{}')>".format(
            self.client_id, self.name)

    def to_dict(self):
        return {"client_id": self.client_id, "name":self.name}


class LockException(Exception):
    pass

Session = sessionmaker()
class ResourceLocker:

    """Utility class for the locking and unlocking of resources
    """

    def __init__(self, url, timeout=3600):
        """Create a new ResourceLocker instance
        Attributes:
          url - URL of backing database
          timeout - (optional) time in seconds to keep connections to database open. Defaults to 3600s
        """
        self.url = url
        engine = create_engine(url, pool_recycle=timeout, echo=False)
        Base.metadata.create_all(engine)
        Session.configure(bind=engine)

    def get_client(self, name, session=None):
        """Get or create a client with the given name"""
        return self._get_object(Client, name=name, session=session)

    def get_resource(self, uri, session=None):
        """Get or create a resource with the given URI"""
        return self._get_object(Resource, uri=uri, session=session)

    def get_client_by_id(self, client_id):
        """Get client with the specified ID"""
        session = Session()
        try:
            return session.query(Client).filter_by(client_id=client_id).first()
        finally:
            session.close()

    def get_resource_by_id(self, resource_id):
        """Get resource with the specified ID"""
        session = Session()
        try:
            return session.query(Resource).filter_by(resource_id=resource_id).first()
        finally:
            session.close()

    def _get_object(self, obj_type, **kwargs):
        """Fetch or create a basic object from the database.
        If the object is not present, create it.
        If it has already been created, return it.
        If a duplicate exists, retry the method.
        """
        has_session = 'session' in kwargs
        session = kwargs.pop('session', Session())
        if session == None:
            has_session = False
            session = Session()
        try:
            obj = session.query(obj_type).filter_by(**kwargs).first()
            if obj:
                return obj
            else:
                obj = obj_type(**kwargs)
                self._lock_db(session)
                session.add(obj)
                session.commit()
                self._unlock_db(session)
                # lazily load attrs so they can be accessed in a detached object
                lazy_load(obj)
                return obj
        except IntegrityError:
            # duplicate entry, so try again to fetch with a fresh session
            kwargs['session'] = session
            return self._get_object(obj_type, **kwargs)
        finally:
            if has_session == False:
                logging.debug("Closing session")
                session.close()

    def get_locks(self, **kwargs):
        """Fetch current locks from the database
        Optional named arguments for filtering:
          lock_type - read or write
          resource - URI of resource
          client - name of client
        Returns:
          List of ResourceLock objects
        """
        session = Session()
        try:
            q = session.query(ResourceLock)
            resource = kwargs.get('resource_uri')
            client = kwargs.get('client_name')
            lock_type = kwargs.get('lock_type')
            if lock_type != None:
                q = q.filter(ResourceLock.lock_type == lock_type)
            if resource != None:
                q = q.join(Resource).filter(Resource.uri == resource)
            if client != None:
                q = q.join(Client).filter(Client.name == client)
            locks = q.all()
            for l in locks:
                lazy_load(l)
            return locks
        finally:
            session.close()

    def get_lock(self, lock_id):
        """Fetch lock with ID from database
        Argument:
          lock_id - ID of lock
        Returns:
          ResourceLock
        """
        session = Session()
        try:
            lock = session.query(ResourceLock).filter_by(resource_lock_id=lock_id).first()
            lazy_load(lock)
            return lock
        finally:
            session.close()


    def lock(self, client_name, resource_uri, lock_type):
        """Lock the specified resource.
        Arguments:
          client - name of client
          resource - URI of resource
          lock_type - read or write
        Returns:
          ResourceLock
        Raises:
          LockException if resource cannot be locked
          ValueException if lock type not read or write
        """
        logging.info("Locking {} for {} for {}".format(client_name, resource_uri, lock_type))
        session = Session()
        client = self.get_client(client_name, session)
        resource = self.get_resource(resource_uri, session)
        try:
            self._lock_db(session)
            if(lock_type == 'read'):
                # can only create if no write locks found on resource
                n_locks = session.query(ResourceLock).filter_by(resource=resource, lock_type='write').count()
                if(n_locks>0):
                    raise LockException("Write lock found on {} - cannot lock for reading {}".format(str(n_locks), resource_uri))
                else:
                    lock = ResourceLock(resource=resource, client=client, lock_type=lock_type)
                    session.add(lock)
                    session.commit()
                    lazy_load(lock)
                    return lock
            elif(lock_type == 'write'):
                # can only create if no other locks found on resource
                n_locks = session.query(ResourceLock).filter_by(resource=resource).count()
                if(n_locks>0):
                    raise LockException("{} lock(s) found on {}".format(str(n_locks), resource_uri))
                else:
                    lock = ResourceLock(resource=resource, client=client, lock_type=lock_type)
                    session.add(lock)
                    session.commit()
                    lazy_load(lock)
                    return lock
            else:
                raise ValueError("Unsupported lock_type: {}".format(str(lock_type)))
            self._unlock_db(session)
        finally:
            session.close()
        return

    def unlock(self, lock):
        """Release the specified lock
        Arguments:
          lock - either ResourceLock or ID of lock
        Returns:
           None
        Raises:
          ValueError if lock not found
        """
        session = Session()
        if(type(lock) is int):
            lock = session.query(ResourceLock).filter_by(resource_lock_id=lock).first()
            if lock == None:
                raise ValueError("No lock found for ID "+str(lock))
        try:
            logging.info("Deleting lock "+str(lock))
            self._lock_db(session)
            session.delete(lock)
            session.commit()
            self._unlock_db(session)
        finally:
            session.close()
        return

    def get_clients(self):
        """Return all current clients
        Returns:
           List of Client objects
        """
        session = Session()
        try:
            clients = session.query(Client).all()
            for client in clients:
                lazy_load(client)
            return clients
        finally:
            session.close()
        return

    def delete_client(self, client):
        """Delete the specified client
        Arguments:
          lock - either name, id or Client object
        Returns:
           None
        Raises:
          ValueError if lock not found
        """
        session = Session()
        if(type(client) is int):
            client = session.query(Client).filter_by(client_id=client).first()
            if client == None:
                raise ValueError("No client found for ID ")
        if(type(client) is str):
            client = session.query(Client).filter_by(name=client).first()
            if client == None:
                raise ValueError("No client found for name")
        try:
            logging.info("Deleting client "+str(client))
            self._lock_db(session)
            session.delete(client)
            session.commit()
            self._unlock_db(session)
        finally:
            session.close()
        return

    def get_resources(self):
        """Return all current resources
        Returns:
           List of Resource objects
        """
        session = Session()
        try:
            resources = session.query(Resource).all()
            for resource in resources:
                lazy_load(resource)
            return resources
        finally:
            session.close()
        return

    def delete_resource(self, resource):
        """Delete the specified client
        Arguments:
          lock - either uri, id or Resource object
        Returns:
           None
        Raises:
          ValueError if lock not found
        """
        session = Session()
        if(type(resource) is int):
            resource = session.query(Resource).filter_by(resource_id=resource).first()
            if resource == None:
                raise ValueError("No client found for ID ")
        if(type(resource) is str):
            resource = session.query(Resource).filter_by(uri=resource).first()
            if resource == None:
                raise ValueError("No client found for name")
        try:
            logging.info("Deleting resource "+str(resource))
            self._lock_db(session)
            session.delete(resource)
            session.commit()
            self._unlock_db(session)
        finally:
            session.close()
        return

    def _lock_db(self, session):
        """Utility to obtain a lock over the MySQL tables to ensure no race condition"""
        if(self.url.startswith('mysql')):
            session.execute('lock table client write, resource write, resource_lock write')

    def _unlock_db(self, session):
        """Utility to obtain release a lock over the MySQL tables"""
        if(self.url.startswith('mysql')):
            session.execute('unlock tables')


