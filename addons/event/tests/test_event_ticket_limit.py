# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.addons.event.tests.common import EventCase
from odoo.tests import tagged


@tagged('event_ticket', 'post_install', '-at_install')
class TestEventTicketLimitPerOrder(EventCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_event = cls.env['event.event'].create({
            'name': 'Ticket Limit Event',
            'date_begin': datetime.now() + timedelta(days=5),
            'date_end': datetime.now() + timedelta(days=6),
            'seats_limited': False,
            'event_ticket_ids': [
                (0, 0, {'name': 'Unlimited', 'seats_max': 0}),
                (0, 0, {'name': 'Unlimited Capped', 'seats_max': 0, 'limit_max_per_order': 5}),
                (0, 0, {'name': 'Limited', 'seats_max': 3, 'limit_max_per_order': 2}),
                (0, 0, {'name': 'Single Seat', 'seats_max': 1}),
            ],
        })
        tickets = cls.test_event.event_ticket_ids
        cls.ticket_unlimited = tickets.filtered(lambda t: t.name == 'Unlimited')
        cls.ticket_unlimited_capped = tickets.filtered(lambda t: t.name == 'Unlimited Capped')
        cls.ticket_limited = tickets.filtered(lambda t: t.name == 'Limited')
        cls.ticket_single = tickets.filtered(lambda t: t.name == 'Single Seat')

    def test_sold_out_ticket_limit_is_zero(self):
        """A sold-out ticket must allow 0 more tickets per order, not the
        'no limit' fallback (odoo/odoo#284098)."""
        self._create_registrations_for_slot_and_ticket(self.test_event, False, self.ticket_single, 1)
        self.assertEqual(self.ticket_single.seats_available, 0)
        self.assertEqual(self.ticket_single._get_current_limit_per_order(), {self.ticket_single.id: 0})

        self.ticket_limited.limit_max_per_order = 0
        self._create_registrations_for_slot_and_ticket(self.test_event, False, self.ticket_limited, 3)
        self.assertEqual(self.ticket_limited.seats_available, 0)
        self.assertEqual(
            self.ticket_limited._get_current_limit_per_order(), {self.ticket_limited.id: 0},
            "A sold-out ticket must not fall back to the event maximum tickets per order",
        )

    def test_available_ticket_limits(self):
        """Unlimited tickets use the per-order limit or the event maximum; limited
        tickets are capped by both the per-order limit and remaining seats."""
        tickets = self.ticket_unlimited | self.ticket_unlimited_capped | self.ticket_limited | self.ticket_single
        self.assertEqual(tickets._get_current_limit_per_order(), {
            self.ticket_unlimited.id: self.test_event.EVENT_MAX_TICKETS,
            self.ticket_unlimited_capped.id: 5,
            self.ticket_limited.id: 2,
            self.ticket_single.id: 1,
        })
        self._create_registrations_for_slot_and_ticket(self.test_event, False, self.ticket_limited, 2)
        self.assertEqual(self.ticket_limited._get_current_limit_per_order(), {self.ticket_limited.id: 1})
