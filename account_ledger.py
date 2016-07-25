# -*- coding: utf-8 -*-
# Copyright 2016 Apulia Software s.r.l. <info@apuliasoftware.it>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning as UserError
import base64


class TempstatisticheMastricnt(models.Model):

    def _pulisci(self):
        self.search([]).unlink()
        return True

    _name = 'tempstatistiche.mastricnt'
    _description = 'Temporaneo stampa mastri conti'

    # ---- PARAMETRI
    p_dadata = fields.Date(required=True)
    p_adata = fields.Date('A Data', required=True)
    p_conto_id = fields.Many2one('account.account')
    p_conto_name = fields.Char()
    p_export_csv = fields.Char()
    # ---- DATI
    data_mov = fields.Date(required=True)
    desc_mov = fields.Char(size=100)
    partner = fields.Char(size=100)
    dare = fields.Float(digits=dp.get_precision('Account'))
    avere = fields.Float(digits=dp.get_precision('Account'))
    saldo = fields.Float(digits=dp.get_precision('Account'))
    saldo_ini = fields.Float(digits=dp.get_precision('Account'))
    saldo_fin = fields.Float(digits=dp.get_precision('Account'))
    ord_id = fields.Float()
    move_name = fields.Char()
    account_id = fields.Many2one('account.account')

    _order = 'account_id, data_mov'

    def carica_dati(self, parametri):
        # ---- Clean Old Data
        self._pulisci()

        # ---- Needed Obj
        moveline_obj = self.env['account.move.line']
        account_obj = self.env['account.account']

        if not parametri.conto:
            accounts = account_obj.search([('type', '!=', 'view')])
        else:
            accounts = [parametri.conto]

        for account in accounts:

            move_ids = moveline_obj.search([
                ('state', '=', 'valid'),
                ('date', '<=', parametri.adata),
                ('date', '>=', parametri.dadata),
                ('account_id', '=', account.id)])

            # ---- Env With Required Context
            new_env = account_obj.with_context(
                date_to=parametri.adata, date_from=parametri.adata,
                state='posted', initial_bal=True)
            saldo_fin = new_env.browse(account.id).balance
            # credit = new_env.browse(account.id).credit
            # debit = new_env.browse(account.id).debit

            # ---- Env for intial Balance
            initial_balance_env = account_obj.with_context(
                date_to=parametri.dadata, date_from=parametri.dadata,
                state='posted', initial_bal=True)
            saldo_ini = initial_balance_env.browse(account.id).balance

            if not move_ids:
                continue
            for riga in move_ids:
                if riga.move_id.state == 'posted':
                    name = ''
                    if riga.partner_id:
                        name = riga.partner_id.name
                    self.create({
                        'data_mov': riga.date,
                        'desc_mov': riga.name,
                        'dare': riga.debit,
                        'avere': riga.credit,
                        'partner': name,
                        'saldo_ini': saldo_ini,
                        'saldo_fin': saldo_fin,
                        'p_dadata': parametri.dadata,
                        'p_adata': parametri.adata,
                        'p_conto_name': '{cod} {name}'.format(
                            cod=parametri.conto.code,
                            name=parametri.conto.name),
                        'move_name': riga.move_id.name,
                        'account_id': account.id,
                    })
            saldo = saldo_ini
            order = 0
            temp_ids = self.search(
                [('account_id', '=', account.id)],
                order='data_mov asc , move_name asc')
            for riga in temp_ids:
                saldo += riga.dare - riga.avere
                order += 1
                riga.write({'saldo': saldo, 'ord_id': order})
        return True


class StampaMastri(models.TransientModel):
    _name = 'stampa.mastri'
    _description = 'par. stampa dei mastri conti'

    def _get_company(self):
        return self.env.user.company_id.id

    dadata = fields.Date(required=True)
    adata = fields.Date(required=True)
    conto = fields.Many2one('account.account')
    export_csv = fields.Boolean(string='Genera CSV')
    state = fields.Selection(
        [('set', 'Set'), ('get', 'Get')], default='set')
    data = fields.Binary('File', readonly=True)
    filename = fields.Char(default='mastri_conto.csv')
    company_id = fields.Many2one('res.company', default=_get_company)

    @api.multi
    def check_report(self):
        self.ensure_one()

        self.env['tempstatistiche.mastricnt'].carica_dati(self)

        if self.export_csv:
            data = self._create_csv()
            self.write({'data': data, 'state': 'get'})
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'stampa.mastri',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                'views': [(False, 'form')],
                'target': 'new',
            }
        else:
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'mastri',
                'datas': {},
            }

    def _create_csv(self):
        data = self.env['tempstatistiche.mastricnt'].search([])
        csv_data_out = '"Data";'
        csv_data_out += '"Descrizione";'
        csv_data_out += '"Partner";'
        csv_data_out += '"Saldo INIZIALE";'
        csv_data_out += '"DARE";'
        csv_data_out += '"AVERE";'
        csv_data_out += '"SALDO";'
        csv_data_out += '\r\n'
        for row in data:
            csv_data_out += '{};'.format(row.data_mov)
            csv_data_out += '{};'.format(row.desc_mov)
            csv_data_out += '{};'.format(row.partner)
            csv_data_out += '{};'.format(row.saldo_ini).replace(".", ",")
            csv_data_out += '{};'.format(row.dare).replace(".", ",")
            csv_data_out += '{};'.format(row.avere).replace(".", ",")
            csv_data_out += '{};'.format(row.saldo).replace(".", ",")
            csv_data_out += '\r\n'
        return base64.encodestring(csv_data_out)
