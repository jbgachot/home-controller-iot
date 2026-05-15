"""Home Assistant WebSocket API client for MicroPython (RFC 6455)"""

import json

import ubinascii as base64
import urandom as random
import uselect
import usocket as socket
import ustruct as struct

from src.logger import logger

_log = logger.prefix("ha_client")


class HAClient:
    _GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

    def __init__(self, url, token):
        url = url.replace("http://", "").replace("https://", "")
        if ":" in url:
            host, port_part = url.split(":", 1)
            self._host = host
            self._port = int(port_part.split("/")[0])
        else:
            self._host = url.split("/")[0]
            self._port = 8123
        self._token = token
        self._socket = None
        self._poller = None
        self.connected = False
        self.authenticated = False
        self._msg_id = 1

    def _next_id(self):
        mid = self._msg_id
        self._msg_id += 1
        return mid

    def _send_frame(self, data, opcode=0x1):
        if isinstance(data, str):
            data = data.encode("utf-8")
        length = len(data)
        frame = bytearray()
        frame.append(0x80 | opcode)
        if length < 126:
            frame.append(0x80 | length)
        elif length < 65536:
            frame.append(0x80 | 126)
            frame.extend(struct.pack(">H", length))
        else:
            frame.append(0x80 | 127)
            frame.extend(struct.pack(">Q", length))
        mask = bytes(random.getrandbits(8) for _ in range(4))
        frame.extend(mask)
        masked = bytearray(length)
        for i in range(length):
            masked[i] = data[i] ^ mask[i % 4]
        frame.extend(masked)
        sent = 0
        while sent < len(frame):
            n = self._socket.send(frame[sent:])
            if n == 0:
                raise RuntimeError("Socket connection broken")
            sent += n

    def _recv_frame(self, blocking=False):
        try:
            if not blocking and not self._poller.poll(0):
                return None
            header = self._socket.recv(2)
            if not header or len(header) < 2:
                return None
            opcode = header[0] & 0x0F
            masked = (header[1] & 0x80) == 0x80
            length = header[1] & 0x7F
            if length == 126:
                lb = self._socket.recv(2)
                if len(lb) < 2:
                    return None
                length = struct.unpack(">H", lb)[0]
            elif length == 127:
                lb = self._socket.recv(8)
                if len(lb) < 8:
                    return None
                length = struct.unpack(">Q", lb)[0]
            mask_key = None
            if masked:
                mask_key = self._socket.recv(4)
                if len(mask_key) < 4:
                    return None
            payload = bytearray()
            remaining = length
            while remaining > 0:
                chunk = self._socket.recv(min(remaining, 4096))
                if not chunk:
                    return None
                payload.extend(chunk)
                remaining -= len(chunk)
            if masked and mask_key:
                for i in range(length):
                    payload[i] ^= mask_key[i % 4]
            if opcode == 0x8:
                self.connected = False
                return None
            if opcode == 0x9:
                self._send_frame(bytes(payload), 0xA)
                return self._recv_frame(blocking)
            if opcode == 0xA:
                return self._recv_frame(blocking)
            return payload.decode("utf-8")
        except Exception as e:
            _log.error("recv error: %s", e)
            self.connected = False
            return None

    def connect(self):
        """Establish WebSocket connection and authenticate with Home Assistant"""
        try:
            self._socket = socket.socket()
            addr = socket.getaddrinfo(self._host, self._port)[0][-1]
            self._socket.connect(addr)
            self._poller = uselect.poll()
            self._poller.register(self._socket, uselect.POLLIN)

            key = base64.b2a_base64(
                bytes(random.getrandbits(8) for _ in range(16))
            ).decode().strip()
            request = (
                f"GET /api/websocket HTTP/1.1\r\n"
                f"Host: {self._host}:{self._port}\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\n"
                "Sec-WebSocket-Version: 13\r\n"
                "\r\n"
            )
            req = request.encode()
            sent = 0
            while sent < len(req):
                n = self._socket.send(req[sent:])
                if n == 0:
                    raise RuntimeError("Socket connection broken")
                sent += n

            response = ""
            while "\r\n\r\n" not in response:
                chunk = self._socket.recv(4096)
                if not chunk:
                    return False
                response += chunk.decode()

            if "HTTP/1.1 101" not in response:
                _log.error("WebSocket upgrade failed")
                return False

            self.connected = True

            auth_req = self._recv_frame(blocking=True)
            if not auth_req:
                return False

            self._send_frame(json.dumps({"type": "auth", "access_token": self._token}))
            resp = self._recv_frame(blocking=True)
            if resp and json.loads(resp).get("type") == "auth_ok":
                self.authenticated = True
                _log.info("Connected to Home Assistant at %s:%s", self._host, self._port)
                return True

            _log.error("Authentication failed")
            return False

        except Exception as e:
            _log.error("Connection error: %s", e)
            self._cleanup()
            return False

    def _cleanup(self):
        if self._socket:
            try:  # noqa: SIM105
                self._socket.close()
            except Exception:
                pass
        self._socket = None
        self._poller = None
        self.connected = False
        self.authenticated = False

    def get_all_states(self):
        """Fetch all entity states from Home Assistant. Returns list or None."""
        if not self.authenticated:
            return None
        try:
            mid = self._next_id()
            self._send_frame(json.dumps({"id": mid, "type": "get_states"}))
            resp = self._recv_frame(blocking=True)
            if resp:
                data = json.loads(resp)
                if data.get("id") == mid and data.get("success"):
                    return data.get("result", [])
                _log.error("get_all_states failed: %s", data.get("error"))
        except Exception as e:
            _log.error("get_all_states error: %s", e)
        return None

    def call_service(self, domain, service, service_data=None, target=None):
        """Call a Home Assistant service. Returns True on success."""
        if not self.authenticated:
            return False
        try:
            mid = self._next_id()
            msg = {"id": mid, "type": "call_service", "domain": domain, "service": service}
            if service_data:
                msg["service_data"] = service_data
            if target:
                msg["target"] = target
            self._send_frame(json.dumps(msg))
            resp = self._recv_frame(blocking=True)
            if resp:
                return json.loads(resp).get("success", False)
        except Exception as e:
            _log.error("call_service error: %s", e)
        return False

    def call_service_response(self, domain, service, service_data=None, target=None):
        """Call a HA service with return_response=True. Returns the response dict or None."""
        if not self.authenticated:
            return None
        try:
            mid = self._next_id()
            msg = {
                "id": mid,
                "type": "call_service",
                "domain": domain,
                "service": service,
                "return_response": True,
            }
            if service_data:
                msg["service_data"] = service_data
            if target:
                msg["target"] = target
            self._send_frame(json.dumps(msg))
            resp = self._recv_frame(blocking=True)
            if resp:
                data = json.loads(resp)
                if data.get("id") == mid and data.get("success"):
                    return data.get("result", {}).get("response")
                _log.error("call_service_response failed: %s", data.get("error"))
        except Exception as e:
            _log.error("call_service_response error: %s", e)
        return None

    def read_message(self):
        """Non-blocking read of the next incoming message. Returns dict or None."""
        if not self.connected:
            return None
        try:
            raw = self._recv_frame(blocking=False)
            if raw:
                return json.loads(raw)
        except Exception as e:
            _log.error("read_message error: %s", e)
            self.connected = False
        return None

    def close(self):
        """Gracefully close the WebSocket connection"""
        if self._socket:
            try:  # noqa: SIM105
                self._send_frame(b"", 0x8)
            except Exception:
                pass
        self._cleanup()
