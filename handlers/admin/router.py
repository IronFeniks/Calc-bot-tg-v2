import logging
from telegram import Update, CallbackQuery
from telegram.ext import ContextTypes
from keyboards.admin import main_menu_keyboard, cancel_button, restore_callback_data, clear_hash_mapping
from handlers.auth import is_admin
from states import AdminStates

logger = logging.getLogger(__name__)

# Словарь для хранения состояний админ-сессий
admin_sessions = {}


def get_admin_session(user_id: int) -> dict:
    """Получить сессию админа"""
    if user_id not in admin_sessions:
        admin_sessions[user_id] = {
            'state': AdminStates.MAIN_MENU,
            'data': {}
        }
    return admin_sessions[user_id]


def clear_admin_session(user_id: int):
    """Очистить сессию админа"""
    if user_id in admin_sessions:
        del admin_sessions[user_id]
    clear_hash_mapping(user_id)


async def admin_router(query: CallbackQuery, user_id: int, action: str, context: ContextTypes.DEFAULT_TYPE):
    """Роутер для callback'ов админки"""
    
    # Импортируем функции из модулей админки
    from . import (
        show_categories_list, add_category_start, add_category_parent, add_category_save,
        edit_category_select, edit_category_name, edit_category_save,
        delete_category_confirm, delete_category_execute,
        show_products_list, add_product_start, save_product_name, save_product_category,
        save_product_multiplicity, save_product_price,
        show_product_link_menu, product_link_node_select, product_toggle_node,
        product_confirm_nodes, product_link_material_select, product_toggle_material,
        product_confirm_materials, product_create_node_start, product_create_node_save_name,
        product_create_node_save_multiplicity, product_create_node_save_price,
        product_create_material_start, product_create_material_save_name,
        product_create_material_save_price, product_finish_setup,
        save_node_quantity, save_material_quantity,
        edit_product_select, edit_product_field, save_product_edit,
        delete_product_confirm, delete_product_execute, search_products,
        show_nodes_list, add_node_start, save_node_name, save_node_category,
        save_node_multiplicity, save_node_price,
        show_node_link_menu, node_link_material_select, node_toggle_material,
        node_confirm_materials, node_create_material_start, node_create_material_save_name,
        node_create_material_save_price, node_finish_setup, save_node_material_quantity,
        edit_node_select, edit_node_field, save_node_edit,
        delete_node_confirm, delete_node_execute, search_nodes,
        show_materials_list, add_material_start, save_material_name, save_material_category,
        save_material_price, edit_material_select, edit_material_field,
        save_material_edit, delete_material_confirm, delete_material_execute, search_materials,
        spec_select_parent, show_spec_menu, link_node_select, link_node_quantity, link_node_save,
        link_material_select, link_material_quantity, link_material_save,
        unlink_spec_confirm, unlink_spec_execute,
        show_admins_list, add_admin_start, add_admin_save,
        delete_admin_confirm, delete_admin_execute, toggle_admin_execute,
        search_start, search_execute, show_search_results
    )
    
    # ==================== ПОВТОРНЫЙ ВХОД В АДМИНКУ ====================
    if action == "mode_admin":
        clear_admin_session(user_id)
        await query.edit_message_text(
            "⚙️ АДМИНИСТРИРОВАНИЕ\n\nГлавное меню:",
            reply_markup=main_menu_keyboard(user_id)
        )
        return
    
    # ==================== ГЛАВНОЕ МЕНЮ ====================
    if action == "admin_categories":
        await show_categories_list(query, user_id)
        return
    
    if action == "admin_products":
        await show_products_list(query, user_id, page=0)
        return
    
    if action == "admin_nodes":
        await show_nodes_list(query, user_id, page=0)
        return
    
    if action == "admin_materials":
        await show_materials_list(query, user_id, page=0)
        return
    
    if action == "admin_spec":
        await spec_select_parent(query, user_id, page=0)
        return
    
    if action == "admin_admins":
        await show_admins_list(query, user_id)
        return
    
    if action == "admin_search":
        await search_start(query, user_id)
        return
    
    if action == "admin_back_to_main":
        clear_admin_session(user_id)
        await query.edit_message_text(
            "⚙️ АДМИНИСТРИРОВАНИЕ\n\nГлавное меню:",
            reply_markup=main_menu_keyboard(user_id)
        )
        return
    
    if action == "admin_exit":
        from handlers.calculator.handlers import start_calculator
        clear_admin_session(user_id)
        await start_calculator(query, context, is_topic=False, lock=None)
        return
    
    # ==================== КАТЕГОРИИ ====================
    if action == "admin_categories_add":
        await add_category_start(query, user_id)
        return
    
    if action == "admin_categories_edit":
        await edit_category_select(query, user_id)
        return
    
    if action == "admin_categories_delete":
        await delete_category_confirm(query, user_id)
        return
    
    if action.startswith("admin_cat_parent_"):
        data = action.replace("admin_cat_parent_", "")
        parent = restore_callback_data(user_id, "admin_cat_parent", data)
        await add_category_parent(query, user_id, parent)
        return
    
    if action.startswith("admin_cat_edit_"):
        data = action.replace("admin_cat_edit_", "")
        category = restore_callback_data(user_id, "admin_cat_edit", data)
        await edit_category_name(query, user_id, category)
        return
    
    if action.startswith("admin_cat_delete_"):
        data = action.replace("admin_cat_delete_", "")
        category = restore_callback_data(user_id, "admin_cat_delete", data)
        await delete_category_execute(query, user_id, category)
        return
    
    # ==================== ИЗДЕЛИЯ ====================
    if action == "admin_products_add":
        await add_product_start(query, user_id)
        return
    
    if action == "admin_products_edit":
        await edit_product_select(query, user_id, page=0)
        return
    
    if action == "admin_products_delete":
        await delete_product_confirm(query, user_id, page=0)
        return
    
    if action == "admin_products_search":
        await search_products(query, user_id)
        return
    
    if action.startswith("admin_products_page_"):
        page = int(action.replace("admin_products_page_", ""))
        await show_products_list(query, user_id, page)
        return
    
    if action.startswith("admin_products_edit_page_"):
        page = int(action.replace("admin_products_edit_page_", ""))
        await edit_product_select(query, user_id, page)
        return
    
    if action.startswith("admin_products_delete_page_"):
        page = int(action.replace("admin_products_delete_page_", ""))
        await delete_product_confirm(query, user_id, page)
        return
    
    if action.startswith("admin_prod_edit_"):
        data = action.replace("admin_prod_edit_", "")
        code = restore_callback_data(user_id, "admin_prod_edit", data)
        await edit_product_field(query, user_id, code)
        return
    
    if action.startswith("admin_prod_delete_"):
        data = action.replace("admin_prod_delete_", "")
        code = restore_callback_data(user_id, "admin_prod_delete", data)
        await delete_product_execute(query, user_id, code)
        return
    
    if action.startswith("admin_prod_cat_"):
        data = action.replace("admin_prod_cat_", "")
        category = restore_callback_data(user_id, "admin_prod_cat", data)
        await save_product_category(query, user_id, category)
        return
    
    if action.startswith("admin_prod_field_"):
        data = action.replace("admin_prod_field_", "")
        restored = restore_callback_data(user_id, "admin_prod_field", data)
        parts = restored.split("_")
        code = parts[0]
        field = "_".join(parts[1:])
        await save_product_edit(query, user_id, code, field)
        return
    
    # ==================== ПРИВЯЗКА К ИЗДЕЛИЮ ====================
    if action.startswith("admin_prod_link_node_"):
        data = action.replace("admin_prod_link_node_", "")
        product_code = restore_callback_data(user_id, "admin_prod_link_node", data)
        await product_link_node_select(query, user_id, page=0)
        return
    
    if action.startswith("admin_prod_link_material_"):
        data = action.replace("admin_prod_link_material_", "")
        product_code = restore_callback_data(user_id, "admin_prod_link_material", data)
        await product_link_material_select(query, user_id, page=0)
        return
    
    if action.startswith("admin_prod_create_node_"):
        data = action.replace("admin_prod_create_node_", "")
        product_code = restore_callback_data(user_id, "admin_prod_create_node", data)
        await product_create_node_start(query, user_id)
        return
    
    if action.startswith("admin_prod_create_material_"):
        data = action.replace("admin_prod_create_material_", "")
        product_code = restore_callback_data(user_id, "admin_prod_create_material", data)
        await product_create_material_start(query, user_id)
        return
    
    if action.startswith("admin_prod_finish_"):
        data = action.replace("admin_prod_finish_", "")
        product_code = restore_callback_data(user_id, "admin_prod_finish", data)
        await product_finish_setup(query, user_id)
        return
    
    if action == "admin_prod_back_to_link_menu":
        await show_product_link_menu(query, user_id)
        return
    
    if action.startswith("admin_prod_toggle_node_"):
        data = action.replace("admin_prod_toggle_node_", "")
        node_code = restore_callback_data(user_id, "admin_prod_toggle_node", data)
        await product_toggle_node(query, user_id, node_code)
        return
    
    if action == "admin_prod_confirm_nodes":
        await product_confirm_nodes(query, user_id)
        return
    
    if action.startswith("admin_prod_nodes_page_"):
        page = int(action.replace("admin_prod_nodes_page_", ""))
        await product_link_node_select(query, user_id, page)
        return
    
    if action.startswith("admin_prod_toggle_material_"):
        data = action.replace("admin_prod_toggle_material_", "")
        mat_code = restore_callback_data(user_id, "admin_prod_toggle_material", data)
        await product_toggle_material(query, user_id, mat_code)
        return
    
    if action == "admin_prod_confirm_materials":
        await product_confirm_materials(query, user_id)
        return
    
    if action.startswith("admin_prod_materials_page_"):
        page = int(action.replace("admin_prod_materials_page_", ""))
        await product_link_material_select(query, user_id, page)
        return
    
    # ==================== УЗЛЫ ====================
    if action == "admin_nodes_add":
        await add_node_start(query, user_id)
        return
    
    if action == "admin_nodes_edit":
        await edit_node_select(query, user_id, page=0)
        return
    
    if action == "admin_nodes_delete":
        await delete_node_confirm(query, user_id, page=0)
        return
    
    if action == "admin_nodes_search":
        await search_nodes(query, user_id)
        return
    
    if action.startswith("admin_nodes_page_"):
        page = int(action.replace("admin_nodes_page_", ""))
        await show_nodes_list(query, user_id, page)
        return
    
    if action.startswith("admin_nodes_edit_page_"):
        page = int(action.replace("admin_nodes_edit_page_", ""))
        await edit_node_select(query, user_id, page)
        return
    
    if action.startswith("admin_nodes_delete_page_"):
        page = int(action.replace("admin_nodes_delete_page_", ""))
        await delete_node_confirm(query, user_id, page)
        return
    
    if action.startswith("admin_node_edit_"):
        data = action.replace("admin_node_edit_", "")
        code = restore_callback_data(user_id, "admin_node_edit", data)
        await edit_node_field(query, user_id, code)
        return
    
    if action.startswith("admin_node_delete_"):
        data = action.replace("admin_node_delete_", "")
        code = restore_callback_data(user_id, "admin_node_delete", data)
        await delete_node_execute(query, user_id, code)
        return
    
    if action.startswith("admin_node_cat_"):
        data = action.replace("admin_node_cat_", "")
        category = restore_callback_data(user_id, "admin_node_cat", data)
        await save_node_category(query, user_id, category)
        return
    
    if action.startswith("admin_node_field_"):
        data = action.replace("admin_node_field_", "")
        restored = restore_callback_data(user_id, "admin_node_field", data)
        parts = restored.split("_")
        code = parts[0]
        field = "_".join(parts[1:])
        await save_node_edit(query, user_id, code, field)
        return
    
    # ==================== ПРИВЯЗКА К УЗЛУ ====================
    if action.startswith("admin_node_link_material_"):
        data = action.replace("admin_node_link_material_", "")
        node_code = restore_callback_data(user_id, "admin_node_link_material", data)
        await node_link_material_select(query, user_id, page=0)
        return
    
    if action.startswith("admin_node_create_material_"):
        data = action.replace("admin_node_create_material_", "")
        node_code = restore_callback_data(user_id, "admin_node_create_material", data)
        await node_create_material_start(query, user_id)
        return
    
    if action.startswith("admin_node_finish_"):
        data = action.replace("admin_node_finish_", "")
        node_code = restore_callback_data(user_id, "admin_node_finish", data)
        await node_finish_setup(query, user_id)
        return
    
    if action == "admin_node_back_to_link_menu":
        await show_node_link_menu(query, user_id)
        return
    
    if action.startswith("admin_node_toggle_material_"):
        data = action.replace("admin_node_toggle_material_", "")
        mat_code = restore_callback_data(user_id, "admin_node_toggle_material", data)
        await node_toggle_material(query, user_id, mat_code)
        return
    
    if action == "admin_node_confirm_materials":
        await node_confirm_materials(query, user_id)
        return
    
    if action.startswith("admin_node_materials_page_"):
        page = int(action.replace("admin_node_materials_page_", ""))
        await node_link_material_select(query, user_id, page)
        return
    
    # ==================== МАТЕРИАЛЫ ====================
    if action == "admin_materials_add":
        await add_material_start(query, user_id)
        return
    
    if action == "admin_materials_edit":
        await edit_material_select(query, user_id, page=0)
        return
    
    if action == "admin_materials_delete":
        await delete_material_confirm(query, user_id, page=0)
        return
    
    if action == "admin_materials_search":
        await search_materials(query, user_id)
        return
    
    if action.startswith("admin_materials_page_"):
        page = int(action.replace("admin_materials_page_", ""))
        await show_materials_list(query, user_id, page)
        return
    
    if action.startswith("admin_materials_edit_page_"):
        page = int(action.replace("admin_materials_edit_page_", ""))
        await edit_material_select(query, user_id, page)
        return
    
    if action.startswith("admin_materials_delete_page_"):
        page = int(action.replace("admin_materials_delete_page_", ""))
        await delete_material_confirm(query, user_id, page)
        return
    
    if action.startswith("admin_mat_edit_"):
        data = action.replace("admin_mat_edit_", "")
        code = restore_callback_data(user_id, "admin_mat_edit", data)
        await edit_material_field(query, user_id, code)
        return
    
    if action.startswith("admin_mat_delete_"):
        data = action.replace("admin_mat_delete_", "")
        code = restore_callback_data(user_id, "admin_mat_delete", data)
        await delete_material_execute(query, user_id, code)
        return
    
    if action.startswith("admin_mat_cat_"):
        data = action.replace("admin_mat_cat_", "")
        category = restore_callback_data(user_id, "admin_mat_cat", data)
        await save_material_category(query, user_id, category)
        return
    
    if action.startswith("admin_mat_field_"):
        data = action.replace("admin_mat_field_", "")
        restored = restore_callback_data(user_id, "admin_mat_field", data)
        parts = restored.split("_")
        code = parts[0]
        field = "_".join(parts[1:])
        await save_material_edit(query, user_id, code, field)
        return
    
    # ==================== СПЕЦИФИКАЦИИ ====================
    if action.startswith("admin_spec_page_"):
        page = int(action.replace("admin_spec_page_", ""))
        await spec_select_parent(query, user_id, page)
        return
    
    if action.startswith("admin_spec_parent_"):
        data = action.replace("admin_spec_parent_", "")
        parent_code = restore_callback_data(user_id, "admin_spec_parent", data)
        await show_spec_menu(query, user_id, parent_code)
        return
    
    if action.startswith("admin_spec_link_node_"):
        data = action.replace("admin_spec_link_node_", "")
        parent_code = restore_callback_data(user_id, "admin_spec_link_node", data)
        await link_node_select(query, user_id, parent_code, page=0)
        return
    
    if action.startswith("admin_spec_node_page_"):
        data = action.replace("admin_spec_node_page_", "")
        restored = restore_callback_data(user_id, "admin_spec_node_page", data)
        parts = restored.split("_")
        parent_code = parts[0]
        page = int(parts[1])
        await link_node_select(query, user_id, parent_code, page)
        return
    
    if action.startswith("admin_spec_link_material_"):
        data = action.replace("admin_spec_link_material_", "")
        parent_code = restore_callback_data(user_id, "admin_spec_link_material", data)
        await link_material_select(query, user_id, parent_code, page=0)
        return
    
    if action.startswith("admin_spec_mat_page_"):
        data = action.replace("admin_spec_mat_page_", "")
        restored = restore_callback_data(user_id, "admin_spec_mat_page", data)
        parts = restored.split("_")
        parent_code = parts[0]
        page = int(parts[1])
        await link_material_select(query, user_id, parent_code, page)
        return
    
    if action.startswith("admin_spec_node_select_"):
        data = action.replace("admin_spec_node_select_", "")
        restored = restore_callback_data(user_id, "admin_spec_node_select", data)
        parts = restored.split("_")
        parent_code = parts[0]
        node_code = "_".join(parts[1:])
        await link_node_quantity(query, user_id, parent_code, node_code)
        return
    
    if action.startswith("admin_spec_mat_select_"):
        data = action.replace("admin_spec_mat_select_", "")
        restored = restore_callback_data(user_id, "admin_spec_mat_select", data)
        parts = restored.split("_")
        parent_code = parts[0]
        mat_code = "_".join(parts[1:])
        await link_material_quantity(query, user_id, parent_code, mat_code)
        return
    
    if action.startswith("admin_spec_unlink_"):
        data = action.replace("admin_spec_unlink_", "")
        restored = restore_callback_data(user_id, "admin_spec_unlink", data)
        parts = restored.split("_")
        parent_code = parts[0]
        child_code = "_".join(parts[1:])
        await unlink_spec_confirm(query, user_id, parent_code, child_code)
        return
    
    if action.startswith("admin_confirm_delete_spec_"):
        data = action.replace("admin_confirm_delete_spec_", "")
        restored = restore_callback_data(user_id, "admin_confirm_delete_spec", data)
        parts = restored.split("_")
        parent_code = parts[0]
        child_code = "_".join(parts[1:])
        await unlink_spec_execute(query, user_id, parent_code, child_code)
        return
    
    # ==================== АДМИНИСТРАТОРЫ ====================
    if action == "admin_admins_add":
        await add_admin_start(query, user_id)
        return
    
    if action == "admin_admins_delete":
        await delete_admin_confirm(query, user_id)
        return
    
    if action.startswith("admin_admins_remove_"):
        data = action.replace("admin_admins_remove_", "")
        admin_id = int(restore_callback_data(user_id, "admin_admins_remove", data))
        await delete_admin_execute(query, user_id, admin_id)
        return
    
    if action.startswith("admin_admins_toggle_"):
        data = action.replace("admin_admins_toggle_", "")
        admin_id = int(restore_callback_data(user_id, "admin_admins_toggle", data))
        await toggle_admin_execute(query, user_id, admin_id)
        return
    
    # ==================== ПОИСК ====================
    if action.startswith("admin_search_page_"):
        page = int(action.replace("admin_search_page_", ""))
        await show_search_results(query, user_id, page)
        return
    
    if action.startswith("admin_search_item_"):
        data = action.replace("admin_search_item_", "")
        code = restore_callback_data(user_id, "admin_search_item", data)
        await show_search_results(query, user_id, 0)
        return
    
    # ==================== ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ ====================
    if action.startswith("admin_confirm_delete_"):
        logger.warning(f"Необработанный confirm_delete: {action}")
        return
    
    # ==================== НЕИЗВЕСТНЫЙ CALLBACK ====================
    logger.warning(f"Неизвестный admin callback: {action}")
    await query.answer("❌ Неизвестная команда", show_alert=True)
