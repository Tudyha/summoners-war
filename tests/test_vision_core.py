import sys
import types
import unittest

from ._package import project_module


android = sys.modules.setdefault("ascript.android", types.ModuleType("ascript.android"))
screen = sys.modules.setdefault(
    "ascript.android.screen",
    types.ModuleType("ascript.android.screen"),
)
system = sys.modules.setdefault(
    "ascript.android.system",
    types.ModuleType("ascript.android.system"),
)


class FakeOcr(object):
    @staticmethod
    def mlkitocr_v2():
        return []


class FakeDevice(object):
    @staticmethod
    def display():
        return types.SimpleNamespace(widthPixels=1080, heightPixels=720)


capture_calls = []


def fake_capture():
    image = object()
    capture_calls.append(image)
    return image


screen.Ocr = FakeOcr
screen.capture_cv = fake_capture
screen.FindColors = object
screen.FindImages = object
system.Device = FakeDevice
system.R = types.SimpleNamespace()

vision_core = project_module("vision.core")


class VisualFrameTests(unittest.TestCase):
    def setUp(self):
        capture_calls[:] = []
        vision_core.begin_visual_frame()

    def test_all_detectors_share_one_lazy_image_per_tick(self):
        first = vision_core.capture_frame_image()
        second = vision_core.capture_frame_image()

        self.assertIs(first, second)
        self.assertEqual(1, len(capture_calls))

    def test_new_tick_invalidates_cached_image(self):
        first = vision_core.capture_frame_image()
        vision_core.begin_visual_frame()
        second = vision_core.capture_frame_image()

        self.assertIsNot(first, second)
        self.assertEqual(2, len(capture_calls))

    def test_fresh_capture_bypasses_tick_cache_for_motion_detection(self):
        cached = vision_core.capture_frame_image()
        fresh = vision_core.capture_fresh_image()

        self.assertIsNot(cached, fresh)
        self.assertEqual(2, len(capture_calls))

    def test_1080x720_is_the_identity_coordinate_space(self):
        self.assertEqual(1080, vision_core.config.REFERENCE_WIDTH)
        self.assertEqual(720, vision_core.config.REFERENCE_HEIGHT)
        self.assertEqual((701, 454), vision_core.scale_point((701, 454)))

    def test_all_calibrated_points_fit_the_supported_display(self):
        for name, point in vision_core.config.POINTS.items():
            with self.subTest(name=name):
                self.assertGreaterEqual(point[0], 0)
                self.assertLessEqual(point[0], 1080)
                self.assertGreaterEqual(point[1], 0)
                self.assertLessEqual(point[1], 720)


if __name__ == "__main__":
    unittest.main()
