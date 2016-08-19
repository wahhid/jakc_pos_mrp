from openerp.osv import fields, osv

class mrp_production(osv.osv):
    _inherit = 'mrp.production'

    def action_in_produce(self, cr, uid, ids, context=None):
        print "Action In Produce"
        return self.pool.get('mrp.product.produce').do_auto_produce(cr, uid, ids, context=None)
    
class mrp_product_produce(osv.osv):
    _inherit = 'mrp.product.produce'
        
    def do_auto_produce(self, cr, uid, ids, context=None):
        #production_id = context.get('active_id', False)
        #assert production_id, "Production Id should be specified in context as a Active ID."
        production_id = ids[0]
        production = self.pool.get('mrp.production').browse(cr, uid, production_id, context=context)
        if production:
            print "Production ID " + str(production.id)
            print "Product ID " + str(production.product_id.id)
            print "Product QTY " + str(production.product_qty)
            print "Run Do Auto Produce"
            #data = self.browse(cr, uid, ids[0], context=context)
            data = {}
            data.update({'product_id':production.product_id.id})
            data.update({'product_qty':production.product_qty})
            data.update({'mode':'consume_produce'})
            print data
            consume_lines = []
            for move_line in production.move_lines:
                consume_line = {}
                consume_line.update({'produce_id': production_id})
                consume_line.update({'product_id': move_line.product_id.id})
                consume_line.update({'lot_id': None})
                consume_line.update({'product_qty': move_line.product_qty})
                consume_lines.append(consume_line)
            data.update({'consume_lines': consume_lines})

            print "Data ->"
            print data.get('product_id')
            print data.get('product_qty')
            print data.get('consume_lines')
            for consume_line in data.get('consume_lines'):
                print consume_line.get('produce_id')
                print consume_line.get('product_id')
                print consume_line.get('product_qty')
                print consume_line.get('lot_id')
            
            self.pool.get('mrp.production').action_auto_produce(cr, uid, production_id,data.get('product_qty'), data.get('mode'), data, context=context)
        else:
            print "Production not found"
        
        return {}