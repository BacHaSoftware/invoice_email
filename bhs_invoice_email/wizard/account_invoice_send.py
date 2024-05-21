# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64

class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _notify_thread_by_email(self, message, recipients_data, msg_vals=False,
                                mail_auto_delete=True,  # mail.mail
                                model_description=False, force_email_company=False, force_email_lang=False,  # rendering
                                subtitles=None,  # rendering
                                resend_existing=False, force_send=True, send_after_commit=True,  # email send
                                **kwargs):
        if self.env.context.get('no_send_mail', False):
            recipients_data = []

        super(MailThread, self)._notify_thread_by_email(message=message, recipients_data=recipients_data, msg_vals=msg_vals,
                                mail_auto_delete=mail_auto_delete, model_description=model_description,
                                force_email_company=force_email_company, force_email_lang=force_email_lang,
                                subtitles=subtitles, resend_existing=resend_existing, force_send=force_send,
                                                            send_after_commit=send_after_commit, **kwargs)


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    send_all = fields.Boolean(string='One email to all recipients', default=False)
    email_to_partner = fields.Many2one('res.partner', string='To')
    cc_partners = fields.Many2many('res.partner', 'account_move_send_partner_rel', 'move_send_id', 'partner_id',
                                   string='CC')

    def _get_wizard_values(self):
        self.ensure_one()
        return {
            'mail_template_id': self.mail_template_id.id,
            'download': self.checkbox_download,
            'send_mail': self.checkbox_send_mail,
            'send_all': self.send_all, #Add wizard values for send all
            'email_cc': self.cc_partners, #Add wizard values for send all
            'email_to': self.email_to_partner, #Add wizard values for send all
        }

    @api.onchange('checkbox_send_mail')
    def onchange_checkbox_send_mail(self):
        if not self.checkbox_send_mail:
            self.send_all = False

    @api.onchange('send_all')
    def onchange_send_all(self):
        if not self.send_all:
            self.email_to_partner = False
            self.cc_partners = False
        else:
            partner_id = self._get_default_mail_partner_ids(self.move_ids, self.mail_template_id, self.mail_lang)
            self.email_to_partner = partner_id if self.move_ids else False
            self.mail_partner_ids = False

    @api.model
    def _send_mails(self, moves_data):
        subtype = self.env.ref('mail.mt_comment')

        # print(moves_data)

        for move, move_data in moves_data.items():
            mail_template = move_data['mail_template_id']
            mail_lang = move_data['mail_lang']
            mail_params = self._get_mail_params(move, move_data)
            if not mail_params:
                continue

            if move_data.get('proforma_pdf_attachment'):
                attachment = move_data['proforma_pdf_attachment']
                mail_params['attachments'].append((attachment.name, attachment.raw))

            email_from = self._get_mail_default_field_value_from_template(mail_template, mail_lang, move, 'email_from')
            model_description = move.with_context(lang=mail_lang).type_name

            if move_data['send_all']:
                self._send_mail_all(
                    move,
                    mail_template,
                    subtype_id=subtype.id,
                    model_description=model_description,
                    email_from=email_from,
                    email_to=move_data.get('email_to'),
                    email_cc=','.join(move_data.get('email_cc').mapped('email')),
                    **mail_params,
                )
            else:
                self._send_mail(
                    move,
                    mail_template,
                    subtype_id=subtype.id,
                    model_description=model_description,
                    email_from=email_from,
                    **mail_params,
                )

    @api.model
    def _send_mail_all(self, move, mail_template, **kwargs):
        """ Function to send invoice by email - one mail to all recipients"""

        email_to = kwargs.get('email_to').email
        email_cc = kwargs.get('email_cc')
        kwargs.pop('partner_ids')
        kwargs.pop('email_to')
        kwargs.pop('email_cc')

        # get list attachment_ids
        mail_attachments = self.mail_attachments_widget
        input_attachments = kwargs.get('attachments')
        name_input_attachments = [att[0] for att in input_attachments]  # name of attachment user input
        for att in mail_attachments:
            if att['id'] is not int:
                for input_att in input_attachments:
                    if input_att[0] == att['name']:
                        att['id'] = self.env['ir.attachment'].sudo().create(
                            {'name': input_att[0], 'datas': base64.encodebytes(input_att[1])}
                        ).id

        attachment_ids = [(4, att['id']) for att in mail_attachments
                          if (type(att['id']) is int and att['name'] in name_input_attachments)]

        mail_values = {
            'email_from': kwargs.get('email_from'),
            'email_to': email_to,
            'email_cc': email_cc,
            'reply_to': mail_template.reply_to or kwargs.get('email_from'),
            'model': 'account.move',
            'res_id': move.id,
            'subject': kwargs.get('subject'),
            'body_html': kwargs.get('body'),
            'email_add_signature': not mail_template,
            'auto_delete': mail_template.auto_delete,
            'mail_server_id': mail_template.mail_server_id.id,
            'reply_to_force_new': False,
            'attachment_ids': attachment_ids,
            'is_notification': True,
            'email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
        }

        # send mail
        mail = self.env['mail.mail'].sudo().create(mail_values)

        # log send mail
        new_message = move.with_context(
            no_new_invoice=True,
            no_send_mail=True,
        ).message_post(
            message_type='comment',
            body=kwargs.get('body'), subject=kwargs.get('subject'),
            subtype_id=kwargs.get('subtype_id'),
            model_description=kwargs.get('model_description'),
            **{
                'email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
                'email_add_signature': not mail_template,
                'mail_auto_delete': mail_template.auto_delete,
                'mail_server_id': mail_template.mail_server_id.id,
                'reply_to_force_new': False,
            },
        )

        # Prevent duplicated attachments linked to the invoice.
        new_message.attachment_ids.write({
            'res_model': new_message._name,
            'res_id': new_message.id,
        })

        mail.send()

