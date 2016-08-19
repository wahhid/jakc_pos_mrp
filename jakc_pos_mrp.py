from openerp.osv import fields, osv
from openerp.tools import float_compare, float_is_zero

class mrp_production(osv.osv):
    _inherit = 'mrp.production'

    def action_in_produce(self, cr, uid, ids, context=None):
        print "Action In Produce"
        return self.pool.get('mrp.product.produce').do_auto_produce(cr, uid, ids, context=None)
    
    
    def action_auto_produce(self, cr, uid, production_id, production_qty, production_mode, wiz=False, context=None):
        """ To produce final product based on production mode (consume/consume&produce).
        If Production mode is consume, all stock move lines of raw materials will be done/consumed.
        If Production mode is consume & produce, all stock move lines of raw materials will be done/consumed
        and stock move lines of final product will be also done/produced.
        @param production_id: the ID of mrp.production object
        @param production_qty: specify qty to produce in the uom of the production order
        @param production_mode: specify production mode (consume/consume&produce).
        @param wiz: the mrp produce product wizard, which will tell the amount of consumed products needed
        @return: True
        """
        stock_mov_obj = self.pool.get('stock.move')
        uom_obj = self.pool.get("product.uom")
        production = self.browse(cr, uid, production_id, context=context)
        production_qty_uom = uom_obj._compute_qty(cr, uid, production.product_uom.id, production_qty, production.product_id.uom_id.id)
        precision = self.pool['decimal.precision'].precision_get(cr, uid, 'Product Unit of Measure')

        main_production_move = False
        if production_mode == 'consume_produce':
            for produce_product in production.move_created_ids:
                if produce_product.product_id.id == production.product_id.id:
                    main_production_move = produce_product.id

        total_consume_moves = []
        if production_mode in ['consume', 'consume_produce']:
            if wiz:
                consume_lines = []
                for cons in wiz.get('consume_lines'):
                    consume_lines.append({'product_id': cons.get('product_id'), 'lot_id': cons.get('lot_id'), 'product_qty': cons.get('product_qty')})
            else:
                consume_lines = self._calculate_qty(cr, uid, production, production_qty_uom, context=context)
            for consume in consume_lines:
                remaining_qty = consume['product_qty']
                for raw_material_line in production.move_lines:
                    if raw_material_line.state in ('done', 'cancel'):
                        continue
                    if remaining_qty <= 0:
                        break
                    if consume['product_id'] != raw_material_line.product_id.id:
                        continue
                    consumed_qty = min(remaining_qty, raw_material_line.product_qty)
                    stock_mov_obj.action_consume(cr, uid, [raw_material_line.id], consumed_qty, raw_material_line.location_id.id,
                                                 restrict_lot_id=consume['lot_id'], consumed_for=main_production_move, context=context)
                    total_consume_moves.append(raw_material_line.id)
                    remaining_qty -= consumed_qty
                if not float_is_zero(remaining_qty, precision_digits=precision):
                    #consumed more in wizard than previously planned
                    product = self.pool.get('product.product').browse(cr, uid, consume['product_id'], context=context)
                    extra_move_id = self._make_consume_line_from_data(cr, uid, production, product, product.uom_id.id, remaining_qty, context=context)
                    stock_mov_obj.write(cr, uid, [extra_move_id], {'restrict_lot_id': consume['lot_id'],
                                                                    'consumed_for': main_production_move}, context=context)
                    stock_mov_obj.action_done(cr, uid, [extra_move_id], context=context)
                    total_consume_moves.append(extra_move_id)

        if production_mode == 'consume_produce':
            # add production lines that have already been consumed since the last 'consume & produce'
            last_production_date = production.move_created_ids2 and max(production.move_created_ids2.mapped('date')) or False
            already_consumed_lines = production.move_lines2.filtered(lambda l: l.date > last_production_date)
            total_consume_moves += already_consumed_lines.ids

            price_unit = 0
            for produce_product in production.move_created_ids:
                is_main_product = (produce_product.product_id.id == production.product_id.id) and production.product_id.cost_method=='real'
                if is_main_product:
                    total_cost = self._calculate_total_cost(cr, uid, total_consume_moves, context=context)
                    production_cost = self._calculate_workcenter_cost(cr, uid, production_id, context=context)
                    price_unit = (total_cost + production_cost) / production_qty_uom

                subproduct_factor = self._get_subproduct_factor(cr, uid, production.id, produce_product.id, context=context)
                lot_id = False
                if wiz:
                    lot_id = wiz.get('lot_id')
                qty = min(subproduct_factor * production_qty_uom, produce_product.product_qty) #Needed when producing more than maximum quantity
                if is_main_product and price_unit:
                    stock_mov_obj.write(cr, uid, [produce_product.id], {'price_unit': price_unit}, context=context)
                new_moves = stock_mov_obj.action_consume(cr, uid, [produce_product.id], qty,
                                                         location_id=produce_product.location_id.id, restrict_lot_id=lot_id, context=context)
                stock_mov_obj.write(cr, uid, new_moves, {'production_id': production_id}, context=context)
                remaining_qty = subproduct_factor * production_qty_uom - qty
                if not float_is_zero(remaining_qty, precision_digits=precision):
                    # In case you need to make more than planned
                    #consumed more in wizard than previously planned
                    extra_move_id = stock_mov_obj.copy(cr, uid, produce_product.id, default={'product_uom_qty': remaining_qty,
                                                                                             'production_id': production_id}, context=context)
                    if is_main_product:
                        stock_mov_obj.write(cr, uid, [extra_move_id], {'price_unit': price_unit}, context=context)
                    stock_mov_obj.action_confirm(cr, uid, [extra_move_id], context=context)
                    stock_mov_obj.action_done(cr, uid, [extra_move_id], context=context)

        self.message_post(cr, uid, production_id, body=_("%s produced") % self._description, context=context)

        # Remove remaining products to consume if no more products to produce
        if not production.move_created_ids and production.move_lines:
            stock_mov_obj.action_cancel(cr, uid, [x.id for x in production.move_lines], context=context)

        print "Send Signal button_produce_done"
        #self.signal_workflow(cr, uid, [production_id], 'button_produce_done')
        return True

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