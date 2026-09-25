import json
import unittest

from src.requests.aggregate import aggregate_requests, build_public_snapshot


def valid_record(
    *,
    request_id="APM-2026-0001",
    lga="Bauchi",
    ward_code="B-001",
    category="water",
    created_at="2026-09-25T10:00:00Z",
    consent=True,
    validation_status="validated",
    **overrides,
):
    record = {
        "request_id": request_id,
        "lga": lga,
        "ward_code": ward_code,
        "address": "Private Test Road",
        "category": category,
        "details": "Private details must not escape.",
        "name": "Private Person",
        "phone": "+2348000000000",
        "email": "private@example.com",
        "consent": consent,
        "created_at": created_at,
        "validation_status": validation_status,
    }
    record.update(overrides)
    return record


class RequestAggregationTests(unittest.TestCase):
    def test_counts_by_lga_category_and_cross_tabulation(self):
        records = [
            valid_record(category="water"),
            valid_record(category="water", request_id="APM-2026-0002"),
            valid_record(category="roads", request_id="APM-2026-0003"),
            valid_record(lga="Bauchi", category="roads", request_id="APM-2026-0004"),
            valid_record(lga="Dambam", category="water", request_id="APM-2026-0005"),
        ]

        result = aggregate_requests(records)

        self.assertEqual(result["total_requests"], 5)
        self.assertEqual(result["by_lga"], {"Bauchi": 4, "Dambam": 1})
        self.assertEqual(result["by_category"], {"roads": 2, "water": 3})
        self.assertEqual(
            result["by_lga_category"],
            {
                "Bauchi": {"roads": 2, "water": 2},
                "Dambam": {"water": 1},
            },
        )

    def test_invalid_and_non_consented_records_are_rejected_and_audited(self):
        records = [
            valid_record(),
            valid_record(request_id="APM-2026-0002", consent=False),
            valid_record(request_id="APM-2026-0003", lga="Not Bauchi"),
            valid_record(request_id="APM-2026-0004", category="transport"),
            valid_record(request_id="APM-2026-0005", created_at="2026-09-25T10:00:00"),
            valid_record(
                request_id="APM-2026-0006",
                validation_status="ward_map_missing",
            ),
        ]

        result = aggregate_requests(records)

        self.assertEqual(result["total_requests"], 1)
        self.assertEqual(result["_audit"]["rejected_records"], 5)
        self.assertEqual(result["_audit"]["non_consented"], 1)
        self.assertEqual(result["_audit"]["invalid_lga"], 1)
        self.assertEqual(result["_audit"]["invalid_category"], 1)
        self.assertEqual(result["_audit"]["invalid_created_at"], 1)
        self.assertEqual(result["_audit"]["invalid_status"], 1)

        public = build_public_snapshot(records, generated_at="2026-09-25T12:00:00Z")
        self.assertEqual(public["total_requests"], 1)
        self.assertNotIn("_audit", public)

    def test_public_projection_excludes_private_fields(self):
        record = valid_record(
            address="House 123, Private Road",
            details="A private request description",
            name="Jane Private",
            phone="+2348000000000",
            email="jane@example.com",
        )

        aggregate = aggregate_requests([record])
        public = build_public_snapshot([record], generated_at="2026-09-25T12:00:00Z")

        for result in (aggregate, public):
            serialized = json.dumps(result, sort_keys=True)
            for private_value in (
                "APM-2026-0001",
                "B-001",
                "House 123",
                "Private Road",
                "private request description",
                "Jane Private",
                "+2348000000000",
                "jane@example.com",
            ):
                self.assertNotIn(private_value, serialized)
        for field in (
            "request_id",
            "ward_code",
            "address",
            "details",
            "name",
            "phone",
            "email",
            "consent",
            "validation_status",
        ):
            self.assertNotIn(field, aggregate)
            self.assertNotIn(field, public)

    def test_optional_private_fields_may_be_missing(self):
        record = {
            "lga": "Bauchi",
            "category": "water",
            "consent": True,
            "created_at": "2026-09-25T10:00:00Z",
        }

        result = aggregate_requests([record])

        self.assertEqual(result["total_requests"], 1)
        self.assertEqual(result["by_lga"], {"Bauchi": 1})
        self.assertEqual(result["suppressed_ward_count"], 0)

    def test_ward_counts_below_threshold_are_suppressed(self):
        records = [
            valid_record(ward_code="B-SMALL", request_id=f"APM-2026-{index:04d}")
            for index in range(1, 5)
        ]
        records.extend(
            valid_record(ward_code="B-OK", request_id=f"APM-2026-{index:04d}")
            for index in range(5, 10)
        )

        result = aggregate_requests(records)

        self.assertEqual(result["total_requests"], 9)
        self.assertEqual(result["suppressed_ward_count"], 1)
        self.assertNotIn("by_ward", result)
        self.assertNotIn("ward_code", result)

    def test_period_filtering_is_inclusive_and_normalizes_to_utc(self):
        records = [
            valid_record(
                request_id="APM-2026-0001",
                created_at="2026-09-25T09:00:00+01:00",
            ),
            valid_record(
                request_id="APM-2026-0002",
                created_at="2026-09-25T09:00:00Z",
            ),
            valid_record(
                request_id="APM-2026-0003",
                created_at="2026-09-25T12:00:00+01:00",
            ),
        ]

        result = aggregate_requests(
            records,
            period_start="2026-09-25T08:00:00Z",
            period_end="2026-09-25T09:00:00Z",
        )

        self.assertEqual(result["total_requests"], 2)
        self.assertEqual(result["reporting_period_start"], "2026-09-25T08:00:00Z")
        self.assertEqual(result["reporting_period_end"], "2026-09-25T09:00:00Z")
        self.assertEqual(result["_audit"]["excluded_by_period"], 1)

    def test_single_supplied_boundary_derives_from_selected_records(self):
        records = [
            valid_record(
                request_id="APM-2026-0001",
                created_at="2026-09-25T08:00:00Z",
            ),
            valid_record(
                request_id="APM-2026-0002",
                created_at="2026-09-25T12:00:00Z",
            ),
        ]

        result = aggregate_requests(records, period_start="2026-09-25T10:00:00Z")

        self.assertEqual(result["total_requests"], 1)
        self.assertEqual(result["reporting_period_start"], "2026-09-25T10:00:00Z")
        self.assertEqual(result["reporting_period_end"], "2026-09-25T12:00:00Z")
        self.assertEqual(result["_audit"]["excluded_by_period"], 1)

    def test_omitted_period_boundaries_are_derived_from_valid_records(self):
        records = [
            valid_record(
                request_id="APM-2026-0001",
                created_at="2026-09-25T12:00:00+01:00",
            ),
            valid_record(
                request_id="APM-2026-0002",
                created_at="2026-09-25T08:00:00Z",
            ),
        ]

        result = aggregate_requests(records)

        self.assertEqual(result["reporting_period_start"], "2026-09-25T08:00:00Z")
        self.assertEqual(result["reporting_period_end"], "2026-09-25T11:00:00Z")

    def test_output_ordering_is_deterministic_independent_of_input_order(self):
        records = [
            valid_record(lga="Zaki", category="security", request_id="APM-2026-0001"),
            valid_record(lga="Bauchi", category="water", request_id="APM-2026-0002"),
            valid_record(lga="Bauchi", category="education", request_id="APM-2026-0003"),
        ]
        reversed_records = list(reversed(records))

        first = aggregate_requests(records)
        second = aggregate_requests(reversed_records)

        self.assertEqual(list(first["by_lga"]), list(second["by_lga"]))
        self.assertEqual(list(first["by_category"]), list(second["by_category"]))
        self.assertEqual(list(first["by_lga_category"]["Bauchi"]), list(second["by_lga_category"]["Bauchi"]))
        self.assertEqual(json.dumps(first, sort_keys=False), json.dumps(second, sort_keys=False))

    def test_public_snapshot_has_fixed_metadata_and_no_audit_data(self):
        records = [valid_record()]
        expected_keys = {
            "reporting_period_start",
            "reporting_period_end",
            "total_requests",
            "by_lga",
            "by_category",
            "by_lga_category",
            "generated_at",
            "small_count_threshold",
            "suppressed_ward_count",
        }

        snapshot = build_public_snapshot(
            records,
            generated_at="2026-09-25T12:00:00+01:00",
            small_count_threshold=5,
        )

        self.assertEqual(set(snapshot), expected_keys)
        self.assertEqual(snapshot["generated_at"], "2026-09-25T11:00:00Z")
        self.assertEqual(snapshot["total_requests"], 1)
        self.assertEqual(snapshot["small_count_threshold"], 5)
        self.assertEqual(snapshot["suppressed_ward_count"], 1)


if __name__ == "__main__":
    unittest.main()
