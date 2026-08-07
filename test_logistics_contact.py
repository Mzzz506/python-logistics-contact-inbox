import unittest

from logistics_contact import parse_form, render_email, submission_id


class LogisticsContactTest(unittest.TestCase):
    def test_form_becomes_a_readable_team_email(self):
        fields = parse_form(
            b"name=Mina+Lee&email=mina%40example.com&shipment_reference=BOX-42&message=Where+is+the+pallet%3F"
        )
        subject, text = render_email(fields)

        self.assertEqual(subject, "Logistics question: BOX-42")
        self.assertIn("Reply email: mina@example.com", text)
        self.assertIn("Where is the pallet?", text)
        self.assertEqual(submission_id(fields), submission_id(dict(reversed(fields.items()))))

    def test_required_fields_are_checked(self):
        with self.assertRaisesRegex(ValueError, "required"):
            parse_form(b"name=&email=invalid&message=")


if __name__ == "__main__":
    unittest.main()
