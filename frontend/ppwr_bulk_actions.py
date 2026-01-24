# PPWR Bulk Action Routes - New implementation with session-based checkboxes
# This file contains the new API routes for the enhanced PPWR tab with bulk actions

from flask import jsonify, request, send_file
from datetime import datetime
from io import BytesIO
import zipfile
import logging

logger = logging.getLogger(__name__)


def register_ppwr_bulk_routes(app, db, SupplierDeclaration, PPWRBOM, PPWRMaterialDeclarationLink, assess_with_files):
    """Register PPWR bulk action routes."""
    
    @app.route('/api/ppwr/declarations/<sku>', methods=['GET'])
    def api_ppwr_declarations_list_v2(sku):
        """Fetch supplier declaration upload table data for PPWR tab.
        
        Returns material data from ppwr_bom with declaration upload status.
        """
        try:
            # Query ppwr_bom for SKU materials
            materials = db.session.query(
                PPWRBOM.material_id,
                PPWRBOM.material_name,
                PPWRBOM.supplier_name
            ).filter_by(sku=sku).all()
            
            # Check which materials have supplier declarations
            material_ids = [m.material_id for m in materials]
            declarations = db.session.query(SupplierDeclaration).filter(
                SupplierDeclaration.material_id.in_(material_ids)
            ).all()
            
            decl_map = {d.material_id: d for d in declarations}
            
            rows = []
            for mat in materials:
                decl = decl_map.get(mat.material_id)
                rows.append({
                    'material_id': mat.material_id,
                    'material_name': mat.material_name or 'Unknown',
                    'supplier_name': mat.supplier_name or 'Unknown',
                    'has_declaration': decl is not None,
                    'declaration_filename': decl.original_filename if decl else None,
                    'uploaded_at': decl.upload_date.isoformat() if decl and decl.upload_date else None,
                    'file_size': decl.file_size if decl else None
                })
            
            return jsonify({'success': True, 'rows': rows, 'total': len(rows)})
        except Exception as e:
            logger.error(f"PPWR declarations list failed: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500


    @app.route('/api/ppwr/mapping/<sku>', methods=['GET'])
    def api_ppwr_mapping_table_v2(sku):
        """Fetch mapping table data showing ppwr_bom ↔ supplier_declarations links.
        
        Uses ppwr_material_declaration_links as left join to show mapping status.
        """
        try:
            # Left join: ppwr_bom → supplier_declarations (direct via material_id)
            query = db.session.query(
                PPWRBOM.material_id,
                PPWRBOM.material_name,
                SupplierDeclaration.original_filename
            ).outerjoin(
                SupplierDeclaration,
                PPWRBOM.material_id == SupplierDeclaration.material_id
            ).filter(PPWRBOM.sku == sku)
            
            results = query.all()
            
            rows = []
            for r in results:
                status = 'Mapped' if r.original_filename else 'Unmapped'
                rows.append({
                    'material_id': r.material_id,
                    'material_name': r.material_name or 'Unknown',
                    'mapped_to': r.original_filename or '—',
                    'status': status
                })
            
            return jsonify({'success': True, 'rows': rows, 'total': len(rows)})
        except Exception as e:
            logger.error(f"PPWR mapping table failed: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500


    @app.route('/api/ppwr/bulk-action', methods=['POST'])
    def api_ppwr_bulk_action_v2():
        """Handle bulk actions: delete, download, evaluate.
        
        Body:
            {
                "action": "delete" | "download" | "evaluate",
                "sku": "SKU123",
                "material_ids": ["MAT1", "MAT2", ...]
            }
        """
        try:
            payload = request.get_json()
            action = payload.get('action')
            sku = payload.get('sku')
            material_ids = payload.get('material_ids', [])
            
            if not action or not sku or not material_ids:
                return jsonify({'success': False, 'error': 'Missing parameters'}), 400
            
            if action == 'delete':
                return _bulk_delete_v2(sku, material_ids)
            elif action == 'download':
                return _bulk_download_v2(sku, material_ids)
            elif action == 'evaluate':
                return _bulk_evaluate_v2(sku, material_ids, assess_with_files)
            else:
                return jsonify({'success': False, 'error': f'Unknown action: {action}'}), 400
                
        except Exception as e:
            logger.error(f"Bulk action failed: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500


    def _bulk_delete_v2(sku, material_ids):
        """Archive supplier declarations for selected materials."""
        try:
            count = db.session.query(SupplierDeclaration).filter(
                SupplierDeclaration.sku == sku,
                SupplierDeclaration.material_id.in_(material_ids)
            ).update({'is_archived': True}, synchronize_session=False)
            
            db.session.commit()
            return jsonify({'success': True, 'deleted': count})
        except Exception as e:
            db.session.rollback()
            logger.error(f"Bulk delete failed: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500


    def _bulk_download_v2(sku, material_ids):
        """Create ZIP file with selected supplier declarations."""
        try:
            declarations = db.session.query(SupplierDeclaration).filter(
                SupplierDeclaration.sku == sku,
                SupplierDeclaration.material_id.in_(material_ids),
                SupplierDeclaration.file_data.isnot(None)
            ).all()
            
            if not declarations:
                return jsonify({'success': False, 'error': 'No declarations found with files'}), 404
            
            # Create ZIP in memory
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for decl in declarations:
                    if decl.file_data:
                        filename = decl.original_filename or f"{decl.material_id}.pdf"
                        zf.writestr(filename, bytes(decl.file_data))
            
            zip_buffer.seek(0)
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            
            return send_file(
                zip_buffer,
                as_attachment=True,
                download_name=f"declarations_{sku}_{timestamp}.zip",
                mimetype='application/zip'
            )
        except Exception as e:
            logger.error(f"Bulk download failed: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500


    def _bulk_evaluate_v2(sku, material_ids, assess_func):
        """Trigger PPWR assessment for selected materials.
        
        Calls FastAPI /ppwr/assess with supplier declaration bytes.
        """
        try:
            declarations = db.session.query(SupplierDeclaration).filter(
                SupplierDeclaration.sku == sku,
                SupplierDeclaration.material_id.in_(material_ids),
                SupplierDeclaration.file_data.isnot(None)
            ).all()
            
            if not declarations:
                return jsonify({'success': False, 'error': 'No declarations with files found'}), 404
            
            # Prepare files for FastAPI
            files = []
            for decl in declarations:
                fname = decl.original_filename or f"{decl.material_id}.pdf"
                files.append((fname, bytes(decl.file_data), 'application/pdf'))
            
            # Call FastAPI /ppwr/assess
            result = assess_func(material_ids, files)
            
            if result and result.get('success'):
                return jsonify({
                    'success': True,
                    'evaluated': len(material_ids),
                    'result': result.get('result', {})
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Assessment failed') if result else 'No response from backend'
                }), 500
                
        except Exception as e:
            logger.error(f"Bulk evaluate failed: {e}", exc_info=True)
            return jsonify({'success': False, 'error': str(e)}), 500
