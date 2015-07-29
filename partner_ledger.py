# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Apulia Software S.r.l.
#    All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv, orm
from tools.translate import _
import time
import openerp.addons.decimal_precision as dp
import unicodedata
import base64


class temp_partnerledger(orm.Model):

    _name = 'temp.partnerledger'

    _columns = {
        'p_fromdate': fields.date('From Date'),
        'p_todate': fields.date('To Date'),
        'p_patner_name': fields.char('Partner Name', size=256),
        'p_company_id': fields.many2one('res.company', 'Company'),
        'date_mov': fields.date('Move Date', required=True),
        'desc_mov': fields.text('Description'),
        'journal_id': fields.many2one('account.journal', 'Journal'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'ref': fields.char('Ref', size=256),
        'dare': fields.float(
            'dare', digits_compute=dp.get_precision('Account')),
        'avere': fields.float(
            'avere', digits_compute=dp.get_precision('Account')),
        'saldo': fields.float(
            'Saldo', digits_compute=dp.get_precision('Account')),
        'credito_ini': fields.float(
            'Credito Iniziale', digits_compute=dp.get_precision('Account')),
        'debito_ini': fields.float(
            'Debito Iniziale', digits_compute=dp.get_precision('Account')),
        'ord_id': fields.float('Ordine'),
        'invoice_id': fields.many2one('account.invoice', 'Invoice'),
        }

    _order = 'date_mov'

    def _clear(self, cr, uid, context):
        ids = self.search(cr, uid, [])
        self.unlink(cr, uid, ids, context)
        return True

    def load_data(self, cr, uid, parameters, context):
        self._clear(cr, uid, context)

        partner_obj = self.pool['res.partner']
        moveline_obj = self.pool['account.move.line']

        # ---- COSTRUISCO LA CONTEXT PER CALCOLARE I SALDI DI APERTURA

        context['state'] = 'posted'
        context['initial_bal'] = True

        context['date_to'] = parameters.to_date
        context['date_from'] = parameters.from_date

        p_partner_name = 'Tutti'
        if parameters.partner_id:
            partner_ids = [parameters.partner_id.id]
            p_partner_name = parameters.partner_id.name
        else:
            if parameters.customer:
                partner_ids = partner_obj.search(
                    cr, uid, [('customer', '=', True)])
            else:
                partner_ids = partner_obj.search(
                    cr, uid, [('supplier', '=', True)])
        create = False
        for partner in partner_obj.browse(cr, uid, partner_ids, context):
            debito_in = partner_obj.browse(
                cr, uid, partner.id, context).credit
            credito_in = partner_obj.browse(
                cr, uid, partner.id, context).debit
            if parameters.customer:
                conto = partner.property_account_receivable.id
            else:
                conto = partner.property_account_payable.id
            filtro_line = [('state', '=', 'valid'),
                           ('date', '<=', parameters.to_date),
                           ('date', '>=', parameters.from_date),
                           ('account_id', '=', conto),
                           ('partner_id', '=', partner.id)]

            move_ids = moveline_obj.search(
                cr, uid, filtro_line, order='invoice')

            if move_ids:
                for riga in moveline_obj.browse(cr, uid, move_ids):
                    if riga.invoice:
                        old_id = self.search(
                            cr, uid,
                            [('partner_id', '=', partner.id),
                             ('invoice_id', '=', riga.invoice.id)])
                        if not old_id:
                            riga_wr = {
                                'date_mov': riga.date,
                                'desc_mov': riga.name,
                                'dare': riga.debit,
                                'avere': riga.credit,
                                'partner_id': partner.id,
                                'credito_ini': credito_in,
                                'debito_ini': debito_in,
                                'p_fromdate': parameters.from_date,
                                'p_todate': parameters.to_date,
                                'p_company_id': riga.company_id.id,
                                'p_partner_name': p_partner_name,
                                'journal_id': riga.journal_id.id,
                                'ref': riga.invoice.number,
                                'invoice_id': riga.invoice.id,
                                }
                            self.create(cr, uid, riga_wr)
                            if not create:
                                create = True
                        else:
                            temp_row = self.browse(cr, uid, old_id[0], context)
                            vals = {
                                'dare': temp_row.dare + riga.debit,
                                'avere': temp_row.avere + riga.credit,
                                }
                            self.write(cr, uid, temp_row.id, vals, context)
                    else:
                        riga_wr = {
                            'date_mov': riga.date,
                            'desc_mov': riga.name,
                            'dare': riga.debit,
                            'avere': riga.credit,
                            'partner_id': partner.id,
                            'credito_ini': credito_in,
                            'debito_ini': debito_in,
                            'p_fromdate': parameters.from_date,
                            'p_todate': parameters.to_date,
                            'p_company_id': riga.company_id.id,
                            'p_partner_name': p_partner_name,
                            'journal_id': riga.journal_id.id,
                            'ref': riga.ref,
                            }
                        self.create(cr, uid, riga_wr)
                        if not create:
                            create = True
                saldo = debito_in - credito_in
                riga_up = {}
                ord = 0
                temp_ids = self.search(
                    cr, uid, [('partner_id', '=', partner.id)],
                    order='date_mov, ref')
                if temp_ids:
                    for riga in self.browse(cr, uid, temp_ids):
                        saldo += riga.dare - riga.avere
                        ord += 1
                        riga_up['saldo'] = saldo
                        riga_up['ord_id'] = ord
                        self.write(cr, uid, riga.id, riga_up)
        if not create:
            raise osv.except_osv(
                _('Error'),
                _('Nothing to print, check the parameters'))
        return True


class wizard_partner_ledger(orm.TransientModel):
    _name = 'wizard.partner.ledger'

    _columns = {
        'from_date': fields.date('From Date', required=True),
        'to_date': fields.date('To Date'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'customer': fields.boolean('Only Customer'),
        'supplier': fields.boolean('Only Supplier'),
        'export_csv': fields.boolean('Export to CSV'),
        'vertical': fields.boolean('Vertical Print')
        }

    _defaults = {
        'to_date': lambda * a: time.strftime('%Y-%m-%d'),
        'from_date': '2001-01-01',
        'customer': True
        }

    def _print_report(self, cr, uid, ids, data=None, context=None):
        if context is None:
            context = {}
        if data is None:
            data = {}
        data['ids'] = context.get('active_ids', [])
        data['model'] = context.get('active_model', 'ir.ui.menu')
        data['form'] = {}
        data['form']['parameters'] = {}
        this = self.browse(cr, uid, ids, context)[0]
        report_name = 'partner_ledger'
        if this.vertical:
            report_name = 'partner_ledger_vertical'

        return {'type': 'ir.actions.report.xml',
                'report_name': report_name,
                'datas': data,
                }

    def check_data(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        parameters = self.browse(cr, uid, ids)[0]
        if parameters.supplier and parameters.customer:
            raise osv.except_osv(
                _('Error !'),
                _('Select customer or supplier'))
        else:
            self.pool['temp.partnerledger'].load_data(
                cr, uid, parameters, context)

        if parameters.export_csv:
            return {
                'name': 'Export Partner Ledger',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'make_csv_partner_ledger',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': context
                }
        else:
            return self._print_report(
                cr, uid, ids, {}, context)

    def onchange_partner_id(self, cr, uid, ids, partner_id, context=None):
        v = {'supplier': False, 'customer': True}
        if not partner_id:
            return {'value': v}
        partner_obj = self.pool['res.partner']
        partner = partner_obj.browse(cr, uid, partner_id, context)
        if partner.supplier:
            v = {'supplier': True, 'customer': False}
            return {'value': v}
        return {'value': v}


class make_csv_partner_ledger(orm.TransientModel):

    _name = "make_csv_partner_ledger"

    _columns = {
        'state': fields.selection((
            ('choose', 'choose'),
            ('get', 'get'),
            )),
        'data': fields.binary('File', readonly=True),
        'file_name': fields.char('File Name', size=128),
        }

    _defaults = {
        'state': lambda * a: 'choose',
        'file_name': 'export_partner_ledger.csv'
        }

    def makecsvpartnerledger(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids)[0]
        idts = self.pool['temp.partnerledger'].search(
            cr, uid, [])
        if idts:
            File = """"""""
            Record = ""
            Record += '"'+"Data Movimento"+'";'
            Record += '"'+"Descrizione"+'";'
            Record += '"'+"Partner"+'";'
            Record += '"'+"Dare"+'";'
            Record += '"'+"Avere"+'";'
            Record += '"'+"Saldo"+'";'
            Record += "\r\n"
            for riga in self.pool['temp.partnerledger'].browse(
                    cr, uid, idts, context):
                Record += '"' + riga.date_mov + '";'
                Record += '"' + unicodedata.normalize(
                    'NFKD', riga.desc_mov).encode('ascii', 'ignore') + '";'
                Record += '"' + unicodedata.normalize(
                    'NFKD', riga.partner_id.name).encode(
                    'ascii', 'ignore')+'";'
                Record += str(riga.dare).replace(".", ",") + ';'
                Record += str(riga.avere).replace(".", ",") + ';'
                Record += str(riga.saldo).replace(".", ",") + ';'
                Record += "\r\n"
            File += Record
            out = base64.encodestring(File)
            self.write(
                cr, uid, ids, {'state': 'get', 'data': out},
                context=context)
            return {
                'name': 'Export Partner Ledger',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'make_csv_partner_ledger',
                'type': 'ir.actions.act_window',
                'res_id': this.id,
                'target': 'new',
                'context': context
                }
        else:
            return {'type': 'ir.actions.act_window_close'}
