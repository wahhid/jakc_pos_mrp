# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2016-Jakc Labs. (<http://www.jakc-labs.com/>)
#
#################################################################################
{
    'name': 'POS: MRP Enhancement',
    'summary': 'Extend MRP Enhancement',
    'version': '1.0',
    'category': 'Point Of Sale',
    "sequence": 1,
    'description': """
Point Of Sale - MRP Enhancment
=====================================

Features:
----------------
    * Add ability to produce product automatically in POS.
    * For Odoo 9

""",
    "author": "Wahyu Hidayat - Jakc Labs.",
    'website': 'http://www.jakc-labs.com',
    'depends': [
        'point_of_sale',
        ],
    'data': [
        'jakc_pos_mrp_workflow.xml',
    ],    
    "installable": True,
    "application": True,
    "auto_install": False,        
}