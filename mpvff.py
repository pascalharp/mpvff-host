#!/bin/env python3

import os
import sys
import json
import struct
import typing
import dataclasses


@dataclasses.dataclass
class MpvResponse:
    request: str
    successful: bool
    info: str


@dataclasses.dataclass
class MpvRequest:
    """
    Class that contains information about the request
    """
    request: str
    url: str

    def process(self) -> MpvResponse:
        """processes the request """
        call: typing.Callable[[MpvRequest], MpvResponse]
        call = MpvRequestOptions.get(
                self.request,
                MpvRequest.__generalError)
        return call(self)

    def _check(self) -> MpvResponse:
        """TODO"""
        return self.__generalError()

    def _play(self) -> MpvResponse:
        """TODO"""
        return self.__generalError()

    def __generalError(self) -> MpvResponse:
        """ invaldi request """
        return MpvResponse(
                request=self.request,
                successful=False,
                info="invalid request"
                )


"""
holds callables for different requests
"""
MpvRequestOptions: typing.Dict[
        str,
        typing.Callable[[MpvRequest], MpvResponse]
        ] = {
            "check": MpvRequest._check,
            "play": MpvRequest._play
            }


"""
unparsable error response
"""
unparsable_response: MpvResponse = MpvResponse(
        request="invalid",
        successful=False,
        info="could not parse request"
        )


def getMessage() -> typing.Dict[str, str]:
    """
    reads a message from stdin, interpretes it as json and converts it
    to python dict
    """
    b_length: bytes = sys.stdin.buffer.read(4)
    if len(b_length) < 4:
        sys.exit(0)
    messageLength: int = struct.unpack('@I', b_length)[0]
    message: str = sys.stdin.buffer.read(messageLength).decode("utf-8")
    return json.loads(message)


def senMessage(message: typing.Dict[str, str]) -> int:
    """
    takes a python dict, converts it to a json string and sends it to
    stdout
    """
    raw: str = json.dumps(message)
    messageLength: bytes = struct.pack('@I', len(raw))
    sys.stdout.buffer.write(messageLength)
    return sys.stdout.buffer.write(bytes(raw, 'utf-8')) + len(messageLength)


def launch_mpv(url: str) -> None:
    """
    launches mpv. This will replace the the current process.
    """
    os.execvp("mpv", ("mpv", "--no-terminal", url))


def spawn(url: str) -> None:
    """
    Forks a new process, then detaches the new one and launches mpv with the
    provided url.
    The process is detached, so that the script can exit and report without
    mpv stopping
    """
    pid = os.fork()
    if pid != 0:
        # parent
        return

    # decouple from parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0)

    # redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    si = open(os.devnull, 'r')
    so = open(os.devnull, 'a+')
    se = open(os.devnull, 'a+')
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

    launch_mpv(url)


if __name__ == "__main__":

    try:
        message = getMessage()
        req = MpvRequest(**message)
        response = req.process()
    except Exception:
        senMessage(vars(unparsable_response))

    exit(0)
