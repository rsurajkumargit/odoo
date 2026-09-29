# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.website_event_sale.tests.common import TestWebsiteEventSaleCommon


@tagged('post_install', '-at_install')
class TestWebsiteEventSaleSeats(TestWebsiteEventSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.event.write({
            'is_multi_slots': True,
            'seats_limited': False,
            'event_slot_ids': [Command.create({
                'date': cls.event.date_begin.date(),
                'start_hour': 9,
                'end_hour': 12,
            })],
        })
        cls.slot = cls.event.event_slot_ids
        cls.ticket.seats_max = 2
        cls.cart = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'website_id': cls.website.id,
        })

    def _verify_quantity(self, new_qty):
        return self.cart._verify_updated_quantity(
            self.env['sale.order.line'],
            self.product_event.id,
            new_qty,
            self.product_event.uom_id.id,
            event_slot_id=self.slot.id,
            event_ticket_id=self.ticket.id,
        )

    def test_unlimited_slot_availability_keeps_quantity(self):
        """An availability of None means 'no limit': the cart must keep the
        requested quantity without warning instead of crashing (odoo/odoo#284098)."""
        self.assertTrue(self.ticket.seats_limited)
        with patch.object(type(self.env['event.event']), '_get_seats_availability', return_value=[None]):
            new_qty, warning = self._verify_quantity(3)
        self.assertEqual(new_qty, 3)
        self.assertFalse(warning)

    def test_limited_slot_availability_clamps_quantity(self):
        """Known remaining seats still clamp the quantity, and a sold-out slot
        ticket adds nothing."""
        new_qty, warning = self._verify_quantity(3)
        self.assertEqual(new_qty, 2)
        self.assertIn('only 2 seats', warning)

        self.env['event.registration'].create([{
            'event_id': self.event.id,
            'event_slot_id': self.slot.id,
            'event_ticket_id': self.ticket.id,
            'name': f'Attendee {idx}',
        } for idx in range(2)])
        new_qty, warning = self._verify_quantity(1)
        self.assertEqual(new_qty, 0)
        self.assertIn('sold out', warning)
