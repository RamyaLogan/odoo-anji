import odoo.http as ohttp
import json

class CourtBookingWebsite(ohttp.Controller):

    @ohttp.route(['/book-court'], type='http', auth='public', website=True)
    def booking_form(self, **kwargs):
        courts = ohttp.request.env['court.details'].sudo().search([('is_active', '=', True)])
        slots = ohttp.request.env['court.time.slot'].sudo().search([('is_active', '=', True)])
        return ohttp.request.render('court_booking.booking_form_template', {
            'courts': courts,
            'slots': slots
        })
    
    @ohttp.route(['/check-availability'], type='json', auth='public', csrf=False)
    def check_availability(self, **post):
        data = json.loads(ohttp.request.httprequest.data.decode('utf-8'))
        booking_date = data.get('booking_date')
        slot_id = int(data.get('slot_id'))
        courts = ohttp.request.env['court.details'].sudo().search([('is_active', '=', True)])
        config = ohttp.request.env['court.facility.config'].sudo().search([], limit=1)

        booked_rackets = sum(
            ohttp.request.env['court.booking'].sudo().search([
                ('booking_date', '=', booking_date),
                ('slot_id', '=', slot_id)
            ]).mapped('racket_qty')
        )
        remaining_rackets = config.total_rackets - booked_rackets
        available_courts = []
        for court in courts:
            is_booked = ohttp.request.env['court.booking'].sudo().search_count([
                ('court_id', '=', court.id),
                ('booking_date', '=', booking_date),
                ('slot_id', '=', slot_id),
            ])
            if is_booked == 0:
                available_courts.append({'id': court.id, 'name': court.name})

        return {
            'available_courts': available_courts,
            'remaining_rackets': remaining_rackets
        }


    @ohttp.route(['/submit-booking'], type='http', auth='public', website=True, csrf=False)
    def submit_booking(self, **post):
        court = ohttp.request.env['court.details'].sudo().browse(int(post.get('court_id')))
        slot = ohttp.request.env['court.time.slot'].sudo().browse(int(post.get('slot_id')))
        config = ohttp.request.env['court.facility.config'].sudo().search([], limit=1)
        partner = ohttp.request.env['res.partner'].sudo().search([('email', '=', post.get('email'))], limit=1)
        if not partner:
            partner = ohttp.request.env['res.partner'].sudo().create({
                'name': post.get('name'),
                'email': post.get('email'),
            })

        booking_date = post.get('booking_date')
        racket_qty = int(post.get('racket_qty') or 0)

        total_booked_rackets = sum(
            ohttp.request.env['court.booking'].sudo().search([
                ('booking_date', '=', booking_date),
                ('slot_id', '=', slot.id)
            ]).mapped('racket_qty')
        )

        if (total_booked_rackets + racket_qty) > config.total_rackets:
            return ohttp.request.redirect('/book-court')

        ohttp.request.env['court.booking'].sudo().create({
            'member_id': partner.id,
            'court_id': court.id,
            'slot_id': slot.id,
            'booking_date': booking_date,
            'racket_qty': racket_qty,
            'status': 'draft'
        })

        return ohttp.request.redirect('/book-court')
