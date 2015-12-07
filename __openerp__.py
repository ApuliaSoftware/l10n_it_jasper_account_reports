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

{
    'name': "Jasper Accounts Reports",
    'version': '0.1',
    'category': 'Reports',
    'description': """Account Reports for Jasper""",
    'author': 'Apulia Software S.r.l.',
    'website': 'info@apuliasoftware.it',
    'license': 'AGPL-3',
    "depends": ['jasper_reports','account'],
    "data": [
        'security/ir.model.access.csv',
        'partner_ledger_view.xml',
        'primanota/primanota_view.xml',
        'report.xml',   
        ],
    "active": False,
    "installable": True
}
