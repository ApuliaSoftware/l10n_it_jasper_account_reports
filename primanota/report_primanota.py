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

from openerp.osv import orm, fields
import base64
import openerp.addons.decimal_precision as dp


class Tempstampprinot(orm.Model):

    _name = "tempstampprinot"
    _description = "Stampa Prima Nota"

    def _pulisci(self, cr, uid, context):
        ids = self.search(cr, uid, [])
        self.unlink(cr, uid, ids, context)
        return True

    _columns = {
        'from_date': fields.date('Da Data Registrazione '),
        'to_date': fields.date('A Data Registrazione'),
        'numreg': fields.char('Numero Reg', size=64, required=True),
        'ref': fields.char('Descrizione Registrazione', size=64),
        'date': fields.date('Data Reg'),
        'narration': fields.text('Narration'),
        'numero_doc': fields.char('Numero Doc.', size=30),
        'data_doc': fields.date('Data Doc.'),
        'protocollo': fields.integer('Protocollo'),
        'account_id': fields.many2one('account.account', 'Account'),
        'account_code': fields.char('Codice Conto', size=64),
        'account_name': fields.char('Des. Conto', size=128),
        'debit': fields.float('Debit',
                              digits_compute=dp.get_precision('Account')),
        'credit': fields.float('Credit',
                               digits_compute=dp.get_precision('Account')),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'des_partner': fields.char('Ragione Sociale', size=64),
        'tax_code_id': fields.many2one('account.tax.code', 'Tax Account'),
        'tax_amount': fields.float('Tax/Base Amount',
                                   digits_compute=dp.get_precision('Account')),
        'account_tax_id': fields.many2one('account.tax', 'Tax'),
        'imponibile': fields.float('Imponibile',
                                   digits_compute=dp.get_precision('Account')),
        'desriga': fields.char('Descrizione RIga', size=64),
        'numpartita': fields.char('Numero Partita Saldata', size=30),
        'numero_doc_partita': fields.char('Numero Doc Partita', size=30),
        'data_doc_partita': fields.date('Data Doc. Partita'),
        'data_scadenza': fields.date('Data Scadenza'),
        'importo_incpag': fields.float(
            'Importo Inc.Pag',
            digits_compute=dp.get_precision('Account')),
    }


class StampaPrimanota(orm.TransientModel):

    _name = "stampa.primanota"

    _columns = {
        'from_date': fields.date('Da Data ', required=True),
        'to_date': fields.date('A Data ', required=True),
        # 'flag_st_scadenze': fields.boolean('Stampa Dettaglio Scadenze'),
        'export_csv': fields.boolean('Genera CSV'),
        'journal_ids' : fields.many2many(
            'account.journal',
            'journal_st_primanota_rel',
            'journal_id',
            'id',
            'Registro',
            help='Vuoto per indicarli tutti'
            ),
    }

    def genera_stampa_primanota(self, cr, uid, ids, context=None):
        # obj = self.pool.get('ir.model.data')
        this = self.browse(cr, uid, ids, context)[0]
        self.pool['tempstampprinot']._pulisci(cr, uid, context)
        moveobj = self.pool['account.move']
        param = self.browse(cr, uid, ids[0])
        cerca = [('date', '>=', param.from_date),
                 ('date', '<=', param.to_date)]
        if this.journal_ids:
            journals = []
            for selected_journal in this.journal_ids:
                journals.append(selected_journal.id)
            cerca.append(('journal_id', 'in', journals))
        ids_move = moveobj.search(cr, uid, cerca)
        if not ids_move:
            raise osv.except_osv(_('Attenzione !'), _(
                'Non ci sono Registrazioni per Questa Selezione'))
        for move in moveobj.browse(cr, uid, ids_move):
            testa = {
                'from_date': param.from_date,
                'to_date': param.to_date,
                'numreg': move.name,
                'ref': move.ref,
                'date': move.date,
                'narration': move.narration,
                'numero_doc': move.ref,
                }
            for move_line in move.line_id:
                riga = {
                    'account_id': move_line.account_id.id,
                    'account_code': move_line.account_id.code,
                    'account_name': move_line.account_id.name,
                    'debit': move_line.debit,
                    'credit': move_line.credit,
                    'partner_id': move_line.partner_id.id,
                    'des_partner': move_line.partner_id.name,
                    'tax_code_id': move_line.tax_code_id.id,
                    'tax_amount': move_line.tax_amount,
                    'account_tax_id': move_line.account_tax_id.id,
                    'desriga': move_line.name,
                    'data_doc': move_line.invoice_date or False,
                }
                # codice in fondo al file
                scad = {}
                riga.update(testa)
                riga.update(scad)
                self.pool['tempstampprinot'].create(cr, uid, riga)

        if param.export_csv:
            return {
                'name': 'Export Prima Nota',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'crea_csv_pnt',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': context
            }
        else:
            data = {}
            return self._print_report(cr, uid, ids, data, param,
                                      context)

    def _print_report(self, cr, uid, ids, data, parametri, context=None):

        if context is None:
            context = {}
        data['ids'] = context.get('active_ids', [])
        data['model'] = context.get('active_model', 'ir.ui.menu')
        data['form'] = {}
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'StPrimaNota',
            'datas': data,
            }


class crea_csv_pnt(orm.TransientModel):
    _name = "crea_csv_pnt"
    _description = "Crea il csv dal temp. Prima Nota"

    _columns = {
        'state': fields.selection((('choose', 'choose'),  # choose accounts
                                   ('get', 'get'),  # get the file
                                   )),
        'data': fields.binary('File', readonly=True),
        'filename': fields.char('File Name', size=64),
        }

    _defaults = {
        'state': lambda *a: 'choose',
        'filename': 'Primanota.csv'
    }

    def generacsvpnt(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids, context)[0]
        idts = self.pool.get('tempstampprinot').search(cr, uid, [],
                                                       context=context)
        if idts:
            costo_dett = self.pool.get('tempstampprinot').browse(cr, uid,
                                                                 idts,
                                                                 context)
            File = """"""""
            Record = ""
            # Record += '"' + "cod_causale" + '";'
            Record += '"' + "Num.Registrazione" + '";'
            Record += '"' + "Riferimento" + '";'
            Record += '"' + "Data Reg." + '";'
            Record += '"' + "Note" + '";'
            Record += '"' + "Numero Doc" + '";'
            Record += '"' + "Data Doc." + '";'
            Record += '"' + "Protocollo" + '";'
            Record += '"' + "Conto" + '";'
            Record += '"' + "Des. Conto " + '";'
            Record += '"' + "Dare" + '";'
            Record += '"' + "Avere" + '";'
            Record += '"' + "Partner" + '";'
            Record += '"' + "Iva" + '";'
            Record += '"' + "Imponibile" + '";'
            Record += '"' + "Des.Riga" + '";'
            Record += '"' + "Num.Partita" + '";'
            Record += '"' + "Doc.Partita" + '";'
            Record += '"' + "Data Doc. Partita" + '";'
            Record += '"' + "Data Scadenza Partita" + '";'
            Record += '"' + "Importo Partita" + '";'
            Record += '"' + "Da Data" + '";'
            Record += '"' + "A Data" + '";'
            Record += '\r\n'
            File += Record
            for riga in self.pool.get('tempstampprinot').browse(cr, uid,
                                                                idts,
                                                                context):
                Record = ""
                # Record += '"' + riga.cod_causale + '";'
                Record += '"' + riga.numreg + '";'
                Record += '"' + unicodedata.normalize('NFKD',
                                                      riga.ref).encode(
                    'ascii', 'ignore') + '";'
                Record += '"' + riga.date + '";'
                if riga.narration:
                    Record += '"' + unicodedata.normalize('NFKD',
                                                          riga.narration).encode(
                        'ascii', 'ignore') + '";'
                else:
                    Record += '"' + ' ";'
                if riga.numero_doc:

                    Record += '"' + unicodedata.normalize('NFKD',
                                                          riga.numero_doc).encode(
                        'ascii', 'ignore') + '";'
                else:
                    Record += '"' + ' ";'
                if riga.data_doc:
                    Record += '"' + riga.data_doc + '";'
                else:
                    Record += '"' + ' ";'

                Record += str(riga.protocollo).replace(".", ",") + ';'
                Record += '"' + riga.account_code + '";'
                Record += '"' + riga.account_name + '";'
                Record += str(riga.debit).replace(".", ",") + ';'
                Record += str(riga.credit).replace(".", ",") + ';'
                if riga.des_partner:
                    Record += '"' + unicodedata.normalize('NFKD',
                                                          riga.des_partner).encode(
                        'ascii', 'ignore') + '";'
                else:
                    Record += '"' + ' ";'
                Record += str(riga.tax_amount).replace(".", ",") + ';'
                Record += str(riga.imponibile).replace(".", ",") + ';'
                if riga.desriga:

                    Record += '"' + unicodedata.normalize('NFKD',
                                                          riga.desriga).encode(
                        'ascii', 'ignore') + '";'
                else:
                    Record += '"' + ' ";'
                if riga.numpartita:
                    Record += '"' + riga.numpartita + '";'
                else:
                    Record += '"' + ' ";'
                if riga.numero_doc_partita:

                    Record += '"' + riga.numero_doc_partita + '";'
                else:
                    Record += '"' + ' ";'
                if riga.data_doc_partita:
                    Record += '"' + riga.data_doc_partita + '";'
                else:
                    Record += '"' + ' ";'
                if riga.data_scadenza:
                    Record += '"' + riga.data_scadenza + '";'
                else:
                    Record += '"' + ' ";'
                Record += str(riga.importo_incpag).replace(".", ",") + ';'
                Record += '"' + riga.from_date + '";'
                Record += '"' + riga.to_date + '";'
                Record += "\r\n"
                File += Record
        out = base64.encodestring(File)
        self.write(cr, uid, ids, {'state': 'get', 'data': out}, context)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'crea_csv_pnt',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': this.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

'''
if param.flag_st_scadenze:
    if move_line.par_saldi:
        for scadenza in move_line.par_saldi:
            if scadenza.name:
                if scadenza.name.name:
                    #import pdb;pdb.set_trace()
                    if scadenza.saldo <> 0:
                        scad = {
                            'numpartita': scadenza.name.name.name,
                            'numero_doc_partita': scadenza.name.name.numero_doc,
                            'data_doc_partita': scadenza.name.name.data_doc,
                            'data_scadenza': scadenza.name.data_scadenza,
                            'importo_incpag': scadenza.saldo or scadenza.name.saldato,

                        }
                        riga.update(testa)
                        riga.update(scad)
                        id_temp = self.pool.get(
                            'tempstampprinot').create(
                            cr, uid, riga)

    else:
        scad = {}
        riga.update(testa)
        riga.update(scad)
        id_temp = self.pool.get(
            'tempstampprinot').create(cr, uid, riga)

        # scrive la riga perchè non salda scadenze
else:
'''