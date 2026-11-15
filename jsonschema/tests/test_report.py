from unittest import TestCase

from jsonschema.exceptions import SchemaError
from jsonschema.report import ErrorItem, Report, summarize


SCHEMA = {
    "type": "object",
    "required": ["name", "age"],
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer", "minimum": 0},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
}


class TestSummarize(TestCase):
    def test_valid_instance_passes(self):
        report = summarize(SCHEMA, {"name": "a", "age": 3})
        self.assertIsInstance(report, Report)
        self.assertTrue(report.ok)
        self.assertEqual(report.errors, [])
        self.assertEqual(report.by_pointer, {})

    def test_single_error_pointer_and_validator(self):
        report = summarize(SCHEMA, {"name": "a", "age": "x"})
        self.assertFalse(report.ok)
        self.assertEqual(len(report.errors), 1)

        item = report.errors[0]
        self.assertIsInstance(item, ErrorItem)
        self.assertEqual(item.pointer, "/age")
        self.assertEqual(item.validator, "type")
        self.assertIn("integer", item.message)

    def test_all_errors_are_aggregated(self):
        report = summarize(SCHEMA, {"age": -1})
        validators = {item.validator for item in report.errors}
        self.assertIn("required", validators)
        self.assertIn("minimum", validators)
        self.assertGreaterEqual(len(report.errors), 2)

    def test_nested_object_pointer(self):
        schema = {
            "type": "object",
            "properties": {
                "a": {
                    "type": "object",
                    "properties": {"b": {"type": "string"}},
                },
            },
        }
        report = summarize(schema, {"a": {"b": 5}})
        self.assertEqual(report.errors[0].pointer, "/a/b")
        self.assertEqual(report.errors[0].validator, "type")

    def test_array_element_pointer(self):
        report = summarize(SCHEMA, {"age": "x", "tags": [1, 2]})
        self.assertIn("/age", report.by_pointer)
        self.assertIn("/tags/0", report.by_pointer)
        self.assertIn("/tags/1", report.by_pointer)
        self.assertEqual(
            [item.pointer for item in report.by_pointer["/tags/0"]],
            ["/tags/0"],
        )

    def test_by_pointer_contains_every_error_once(self):
        report = summarize(SCHEMA, {"age": -1})
        flattened = [
            item
            for group in report.by_pointer.values()
            for item in group
        ]
        self.assertEqual(flattened, report.errors)

    def test_root_level_error_uses_empty_pointer(self):
        report = summarize({"type": "string"}, 5)
        self.assertEqual(report.errors[0].pointer, "")
        self.assertIn("", report.by_pointer)

    def test_pointer_escapes_tilde_and_slash(self):
        schema = {
            "type": "object",
            "properties": {
                "a/b": {"type": "string"},
                "c~d": {"type": "string"},
            },
        }
        report = summarize(schema, {"a/b": 1, "c~d": 2})
        pointers = {item.pointer for item in report.errors}
        self.assertIn("/a~1b", pointers)
        self.assertIn("/c~0d", pointers)

    def test_invalid_schema_raises_schema_error(self):
        with self.assertRaises(SchemaError):
            summarize({"type": "nope"}, {})

    def test_boolean_schemas_are_supported(self):
        self.assertTrue(summarize(True, {}).ok)
        report = summarize(False, {})
        self.assertFalse(report.ok)
        self.assertEqual(report.errors[0].pointer, "")
        self.assertIsNone(report.errors[0].validator)
