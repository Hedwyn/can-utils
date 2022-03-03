"""
Implementation of a simple and fast CAN bus using a c extension (partially based on can-utils)
Works for Linux only.
Provides the subset of functionalities necessary for ETKA.
If unsupported features are called, reverts to a regular socketcan bus.

author: Baptiste Pestourie
date: Mar 2022
"""


from candump import loop, recv, terminate
import can
from can.interfaces.socketcan import socketcan
from can.message import Message
from threading import Thread
import logging
import sys

#---------------------------------------------------------------------------
#  Configuring this test module's logger. 
#---------------------------------------------------------------------------
FORMAT = "|--> %(funcName)20s(): %(message)s"
_logger = logging.getLogger(__name__)
_logger.setLevel( logging.DEBUG )
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter(FORMAT))
_logger.addHandler(_handler)

class NotSupportedError(Exception):
    """Raised when some parameters are not supported for the fast-receive implementation"""
    pass

class LowLevelBus(socketcan.SocketcanBus):
    def __init__(self, *args, wait_before_start: bool = False, **kwargs):
        """
        Parameters
        ----------
        wait_before_start : bool
            If enabled, the reception thread is not started right away"""
        super().__init__(*args, **kwargs)
        self.fast_reader = Thread(target=self.poll)
        self._on = False
        # super().recv = self.recv

        if not wait_before_start:
            self.fast_reader.start()
            self._on = True

    def poll(self):
        """
        Main function of the fast-receive thread."""
        try:
            loop()
        except (KeyboardInterrupt, SystemError):
            _logger.debug("Stopping thread...")
            return

    def exc_handler(self, exc: Exception):
        """Handles the exception raised on receiver/fast receive
        
        Parameters
        ----------
        exc : Exception
            The exception that was raised, must come from recv or fast_recv
        """
        if isinstance(exc, TypeError):
            # if None got returned from recv, returning None
            return None
        
        elif isinstance(exc, AssertionError):
            # if assertion failed, disabling the fast receive and defaulting to the Python implementation
            self.mutate()
            return None
        
        elif isinstance(exc, SystemError):
            # happens when the program is about to terminate
            # we don't need to do anything specific  it is handled elsewhere, returning None is enough
            self._on = False
            return None
        
        else:
            raise
    
    def recv(self, timeout=0.0):
        """
        Overrides the python-can Bus recv() method to use the faster implementation.
        Calls by default fast_recv(). Python-can has some wrappers around rec() methods;
        Call recv() directly if you want to enable this wrappers or for backward-compliance, otherwise,
        call fast_recv directly.

        Parameters
        ----------
        timeout : float
            Not implemented yet. Only there to prevent breaking existing implementations using timeout = 0.
            If requesting any value other than 0, raises NotImplementedError
        """
        try:
            if timeout > 0:
                raise NotImplementedError("Timeout not implemented, should always be 0 for now")
            return(self.fast_recv())
        except Exception as e:
            self.exc_handler(e)

    def fast_recv(self):
        """
        Calls the c-extension to receive a can message.
        This is a minimalist implementation in which most of the parameters are defaulted.
        If assertions are enabled, 
        """

        try:
            can_id, lgth, data, ts  = recv()
            return Message(arbitration_id=can_id, dlc=lgth, data=data,timestamp=ts)

        except Exception as e:
            self.exc_handler(e)

    def mutate(self):
        """Mutates this class back to the parent implementation.
        Reverts overriden methods to their original implementations and change __class__ attribute so 
        there is virtually no difference from outside"""
        # bringing back parent's receive
        self.recv = super().recv   
        def stub(*args, **kwargs):
            """Notifying that this function is not supported anymore"""
            raise NotSupportedError("It seems that your requested parameters are not supported by the fast receive implementation.")
        self.fast_recv = stub
        # hacky way to 'revert' this class to the parent one.
        # This is okay here as we are 100% similar to parent at that point
        # Not really required at the point, but that may avoids future issues when type-checking    
        self.__class__ = super().__class__     

class EtkaBus(socketcan.SocketcanBus):
    """
    Overrides recv() method from python-can Bus to provide a faster implementation
    """
    @classmethod
    def factory(cls, *args, **kwargs):
        """
        Returns an EtkaBus if the parameters are eligible, otherwise, a regular socketcan Bus is returned.
        """
        try:
            return(LowLevelBus(*args, **kwargs))
        except (ValueError, NotSupportedError):
            return(socketcan.SocketcanBus(*args, **kwargs))


if __name__ == "__main__":
    # small test snippet. Use together with a CAN emitter to try it out.
    can.rc['interface'] = 'socketcan'
    bus = EtkaBus.factory(channel='vcan0', bitrate=500000)
    print(type(bus))
    try:
        while bus.fast_reader.is_alive():
            msg = bus.recv()
            if msg is not None:
                _logger.debug(msg)
    except KeyboardInterrupt:
        terminate()
        print("Waiting for reader thread to terminate...")
        while bus.fast_reader.is_alive(): pass
        print("Done")


