from .router import admin_router
from .categories import (
    show_categories_list,
    add_category_start,
    add_category_parent,
    add_category_save,
    edit_category_select,
    edit_category_name,
    edit_category_save,
    delete_category_confirm,
    delete_category_execute
)
from .products import (
    show_products_list,
    add_product_start,
    save_product_name,
    save_product_category,
    save_product_multiplicity,
    save_product_price,
    edit_product_select,
    edit_product_field,
    save_product_edit,
    delete_product_confirm,
    delete_product_execute,
    search_products
)
from .nodes import (
    show_nodes_list,
    add_node_start,
    save_node_name,
    save_node_category,
    save_node_multiplicity,
    save_node_price,
    edit_node_select,
    edit_node_field,
    save_node_edit,
    delete_node_confirm,
    delete_node_execute,
    search_nodes
)
from .materials import (
    show_materials_list,
    add_material_start,
    save_material_name,
    save_material_category,
    save_material_price,
    edit_material_select,
    edit_material_field,
    save_material_edit,
    delete_material_confirm,
    delete_material_execute,
    search_materials
)
from .specifications import (
    spec_select_parent,
    show_spec_menu,
    link_node_select,
    link_node_quantity,
    link_node_save,
    link_material_select,
    link_material_quantity,
    link_material_save,
    unlink_spec_confirm,
    unlink_spec_execute
)
from .admins import (
    show_admins_list,
    add_admin_start,
    add_admin_save,
    delete_admin_confirm,
    delete_admin_execute,
    toggle_admin_execute
)
from .search import (
    search_start,
    search_execute,
    show_search_results
)

__all__ = [
    'admin_router',
    # Categories
    'show_categories_list',
    'add_category_start',
    'add_category_parent',
    'add_category_save',
    'edit_category_select',
    'edit_category_name',
    'edit_category_save',
    'delete_category_confirm',
    'delete_category_execute',
    # Products
    'show_products_list',
    'add_product_start',
    'save_product_name',
    'save_product_category',
    'save_product_multiplicity',
    'save_product_price',
    'edit_product_select',
    'edit_product_field',
    'save_product_edit',
    'delete_product_confirm',
    'delete_product_execute',
    'search_products',
    # Nodes
    'show_nodes_list',
    'add_node_start',
    'save_node_name',
    'save_node_category',
    'save_node_multiplicity',
    'save_node_price',
    'edit_node_select',
    'edit_node_field',
    'save_node_edit',
    'delete_node_confirm',
    'delete_node_execute',
    'search_nodes',
    # Materials
    'show_materials_list',
    'add_material_start',
    'save_material_name',
    'save_material_category',
    'save_material_price',
    'edit_material_select',
    'edit_material_field',
    'save_material_edit',
    'delete_material_confirm',
    'delete_material_execute',
    'search_materials',
    # Specifications
    'spec_select_parent',
    'show_spec_menu',
    'link_node_select',
    'link_node_quantity',
    'link_node_save',
    'link_material_select',
    'link_material_quantity',
    'link_material_save',
    'unlink_spec_confirm',
    'unlink_spec_execute',
    # Admins
    'show_admins_list',
    'add_admin_start',
    'add_admin_save',
    'delete_admin_confirm',
    'delete_admin_execute',
    'toggle_admin_execute',
    # Search
    'search_start',
    'search_execute',
    'show_search_results'
]
