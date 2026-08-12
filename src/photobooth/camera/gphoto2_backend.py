"""DSLR backend via gphoto2 -- primary target is a tethered Canon EOS 1000D.

Should work with any gphoto2-supported DSLR (see gphoto.org's compatibility
list) since it only relies on the generic capture/preview/file-transfer API.
"""

from __future__ import annotations

import io

from PIL import Image

from photobooth.camera.base import CameraBackend, CameraUnavailableError, Capture, Frame


class Gphoto2Backend(CameraBackend):
    name = "gphoto2"

    def __init__(self) -> None:
        self._gp = None
        self._camera = None

    def open(self) -> None:
        try:
            import gphoto2 as gp
        except ImportError as exc:
            raise CameraUnavailableError("python-gphoto2 is not installed (Linux only)") from exc

        try:
            camera = gp.Camera()
            camera.init()
        except gp.GPhoto2Error as exc:
            raise CameraUnavailableError(f"No gphoto2-compatible camera detected: {exc}") from exc

        self._gp = gp
        self._camera = camera

    def close(self) -> None:
        if self._camera is not None:
            self._camera.exit()
            self._camera = None

    @property
    def has_preview(self) -> bool:
        return True

    def preview_frame(self) -> Frame | None:
        assert self._camera is not None and self._gp is not None
        try:
            camera_file = self._camera.capture_preview()
        except self._gp.GPhoto2Error:
            return None
        raw = bytes(camera_file.get_data_and_size())
        image = Image.open(io.BytesIO(raw)).convert("RGB")
        return Frame(rgb_bytes=image.tobytes(), width=image.width, height=image.height)

    def capture(self) -> Capture:
        assert self._camera is not None and self._gp is not None
        gp = self._gp

        file_path = self._camera.capture(gp.GP_CAPTURE_IMAGE)
        camera_file = self._camera.file_get(
            file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL
        )
        data = bytes(camera_file.get_data_and_size())
        extension = file_path.name.rsplit(".", 1)[-1].lower() if "." in file_path.name else "jpg"

        try:
            self._camera.file_delete(file_path.folder, file_path.name)
        except gp.GPhoto2Error:
            pass  # not fatal -- just means the card slowly fills up over an event

        return Capture(data=data, extension=extension)
