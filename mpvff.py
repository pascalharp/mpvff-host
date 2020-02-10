#!/bin/env python3

import os
import sys
import json
import struct
import typing
import dataclasses
import subprocess

"""
globals
"""

mpv_ipc_file: str = "/tmp/mpvff-socket"


@dataclasses.dataclass
class MpvResponse:
    request: str
    successful: bool
    url: str = ""
    info: str = ""

    def generate(self) -> typing.Dict[str, typing.Any]:
        """
        Generate a json dict from the class
        currently only allows flat json objects, empty strings are removed
        """
        jDict: typing.Dict[str, typing.Any] = {}
        for k, v in vars(self).items():
            if isinstance(v, (bool, int)):
                jDict[k] = v
            elif isinstance(v, (str)):
                if len(v) > 0:
                    jDict[k] = v
        return jDict


@dataclasses.dataclass
class MpvRequest:
    """
    Class that contains information about the request
    """
    request: str
    url: str
    id: int

    def process(self) -> MpvResponse:
        """processes the request """
        call: typing.Callable[[MpvRequest], MpvResponse]
        call = MpvRequestOptions.get(
                self.request,
                MpvRequest.__generalError)
        return call(self)

    def _check(self) -> MpvResponse:
        """
        Calls youtube-dl without actually downloading the content
        to check if the url is valid.
        """
        try:
            youtube_dl_call: typing.List[str] = [
                    "youtube-dl",
                    "--quiet",
                    "--skip-download",
                    self.url
                    ]
            subprocess.check_call(
                    youtube_dl_call,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                    )
            return MpvResponse(
                    request=self.request,
                    successful=True,
                    url=self.url,
                    info="Valid url"
                    )

        except Exception as e:
            return MpvResponse(
                    request=self.request,
                    successful=False,
                    url=self.url,
                    info="No playable content found"
                    )

    def _play(self) -> MpvResponse:
        """
        Starts mpv with the given url
        """
        try:
            spawn(self.url)
            return MpvResponse(
                    request=self.request,
                    successful=True,
                    url=self.url,
                    info="sent to mpv"
                    )
        except Exception as e:
            return MpvResponse(
                    request=self.request,
                    successful=False,
                    url=self.url,
                    info="failed to launch mpv"
                    )

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
        info="failed to parse request"
        )


def error(*args, **kwargs) -> None:
    """
    Prints to stderr
    """
    print(*args, file=sys.stderr, **kwargs)


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


def sendMessage(message: typing.Dict[str, str]) -> int:
    """
    takes a python dict, converts it to a json string and sends it to
    stdout
    """
    raw: str = json.dumps(message)
    messageLength: bytes = struct.pack('@I', len(raw))
    sys.stdout.buffer.write(messageLength)
    return sys.stdout.buffer.write(bytes(raw, 'utf-8')) + len(messageLength)


def launch_mpv(url: str, id: int) -> None:
    """
    launches mpv. This will replace the the current process.
    """
    os.execvp(
        "mpv",
        (
            "mpv",
            "--no-terminal",
            "--input-ipc-server={}".format(mpv_ipc_file + ".{}".format(id)),
            url
        )
    )


def spawn(url: str, id: int) -> None:
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
        sendMessage(response.generate())
    except Exception:
        sendMessage(unparsable_response.generate())

    exit(0)
