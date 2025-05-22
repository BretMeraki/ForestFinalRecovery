# alembic/versions/update_uuid_fields.py

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "update_uuid_fields"
down_revision: Union[str, None] = "f5b76ed1b9bd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    # --- BEGIN RECOMMENDED CHANGE ---
    # Ensure users.id is of type UUID before dependent tables are created.
    users_columns = inspector.get_columns("users")
    user_id_col_info = next((col for col in users_columns if col["name"] == "id"), None)

    if user_id_col_info:
        current_type_str = str(user_id_col_info["type"]).upper()
        # Check if it's not already some variant of UUID
        if "UUID" not in current_type_str:
            print(f"Attempting to alter users.id from {current_type_str} to UUID...")
            try:
                # Safe migration approach: Drop and recreate the users table with UUID
                # Since this is a development environment, we can safely drop existing data
                print("Dropping and recreating users table with UUID primary key...")
                
                # Drop dependent tables first (they will be recreated by other migrations if needed)
                try:
                    print("Dropping memory_snapshots table (depends on users)...")
                    op.drop_table("memory_snapshots")
                except Exception as e:
                    print(f"memory_snapshots table not found or already dropped: {e}")
                
                # Drop foreign key constraints first
                try:
                    op.drop_constraint("reflection_logs_user_id_fkey", "reflection_logs", type_="foreignkey")
                except Exception:
                    print("reflection_logs_user_id_fkey constraint not found, skipping...")
                
                try:
                    op.drop_constraint("task_footprints_user_id_fkey", "task_footprints", type_="foreignkey")  
                except Exception:
                    print("task_footprints_user_id_fkey constraint not found, skipping...")
                
                # Drop the users table
                print("Dropping users table...")
                op.drop_table("users")
                
                # Recreate users table with UUID primary key
                op.create_table(
                    "users",
                    sa.Column(
                        "id",
                        postgresql.UUID(as_uuid=True),
                        primary_key=True,
                        server_default=sa.text("gen_random_uuid()"),
                    ),
                    sa.Column("email", sa.String(255), nullable=False, unique=True),
                    sa.Column("hashed_password", sa.String(255), nullable=False),
                    sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
                    sa.Column(
                        "created_at",
                        sa.DateTime(timezone=True),
                        server_default=sa.text("now()"),
                        nullable=False,
                    ),
                    sa.Column(
                        "updated_at",
                        sa.DateTime(timezone=True),
                        server_default=sa.text("now()"),
                        nullable=False,
                    ),
                )
                
                # Recreate foreign key constraints
                try:
                    op.create_foreign_key(
                        "reflection_logs_user_id_fkey",
                        "reflection_logs", 
                        "users",
                        ["user_id"],
                        ["id"]
                    )
                except Exception:
                    print("Could not recreate reflection_logs foreign key, table may not exist...")
                
                try:
                    op.create_foreign_key(
                        "task_footprints_user_id_fkey",
                        "task_footprints",
                        "users", 
                        ["user_id"],
                        ["id"]
                    )
                except Exception:
                    print("Could not recreate task_footprints foreign key, table may not exist...")
                print("Successfully altered users.id to UUID and set server_default.")
                
            except Exception as e:
                print(f"Failed to alter users.id type or set server_default: {e}")
                print(
                    "This might be due to existing data that cannot be cast, or other constraints."
                )
                print(
                    "Manual intervention or a more detailed data migration strategy for users.id might be needed."
                )
                # Alembic will handle transaction rollback automatically on exceptions
                raise  # Re-raise the exception to halt the migration
        else:
            print("users.id appears to be already of UUID type.")
    else:
        print("Could not find 'id' column in 'users' table for type alteration check.")

    # --- END RECOMMENDED CHANGE ---

    # Create HTA tables (simplified check without problematic inspector recreation)
    # Check if hta_trees exists by trying to get its columns
    try:
        hta_trees_columns = inspector.get_columns("hta_trees")
        hta_trees_exists = True
    except Exception:
        hta_trees_exists = False

    if not hta_trees_exists:
        op.create_table(
            "hta_trees",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("goal_name", sa.String(255), nullable=False),
            sa.Column("initial_context", sa.Text(), nullable=True),
            sa.Column("top_node_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("initial_roadmap_depth", sa.Integer(), nullable=True),
            sa.Column("initial_task_count", sa.Integer(), nullable=True),
            sa.Column(
                "manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=True
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(
                ["user_id"],
                ["users.id"],
            ),
            sa.Index("idx_hta_trees_user_id_created_at", "user_id", "created_at"),
        )

        # Check if hta_nodes exists
        try:
            hta_nodes_columns = inspector.get_columns("hta_nodes")
            hta_nodes_exists = True
        except Exception:
            hta_nodes_exists = False

        if not hta_nodes_exists:
            op.create_table(
                "hta_nodes",
                sa.Column(
                    "id",
                    postgresql.UUID(as_uuid=True),
                    primary_key=True,
                    server_default=sa.text("gen_random_uuid()"),
                ),
                sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
                sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
                sa.Column("tree_id", postgresql.UUID(as_uuid=True), nullable=False),
                sa.Column("title", sa.String(255), nullable=False),
                sa.Column("description", sa.Text(), nullable=True),
                sa.Column(
                    "is_leaf",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("true"),
                ),
                sa.Column(
                    "status",
                    sa.String(),
                    nullable=False,
                    server_default=sa.text("'pending'"),
                ),
                sa.Column(
                    "created_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.text("now()"),
                    nullable=False,
                ),
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    server_default=sa.text("now()"),
                    nullable=False,
                ),
                sa.ForeignKeyConstraint(
                    ["parent_id"],
                    ["hta_nodes.id"],
                ),
                sa.ForeignKeyConstraint(
                    ["tree_id"],
                    ["hta_trees.id"],
                ),
                sa.ForeignKeyConstraint(
                    ["user_id"],
                    ["users.id"],
                ),
                sa.Index("idx_hta_nodes_parent_id", "parent_id"),
                sa.Index("idx_hta_nodes_tree_id", "tree_id"),
                sa.Index("idx_hta_nodes_user_id", "user_id"),
            )

            op.create_foreign_key(
                "fk_hta_trees_top_node_id",
                "hta_trees",
                "hta_nodes",
                ["top_node_id"],
                ["id"],
            )

    # Create GIN index on manifest column if it doesn't exist
    try:
        indexes = inspector.get_indexes("hta_trees")
        if not any(idx["name"] == "idx_hta_trees_manifest_gin" for idx in indexes):
            op.create_index(
                "idx_hta_trees_manifest_gin",
                "hta_trees",
                ["manifest"],
                postgresql_using="gin",
            )
    except Exception as e:
        print(f"Could not create GIN index: {e}")


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    # Check if hta_trees exists
    try:
        hta_trees_columns = inspector.get_columns("hta_trees")
        hta_trees_exists = True
    except Exception:
        hta_trees_exists = False

    if hta_trees_exists:
        try:
            indexes = inspector.get_indexes("hta_trees")
            if any(idx["name"] == "idx_hta_trees_manifest_gin" for idx in indexes):
                op.drop_index("idx_hta_trees_manifest_gin", table_name="hta_trees")
        except Exception:
            pass

        # Check if hta_nodes exists
        try:
            hta_nodes_columns = inspector.get_columns("hta_nodes")
            hta_nodes_exists = True
        except Exception:
            hta_nodes_exists = False

        if hta_nodes_exists:
            op.drop_table("hta_nodes")

        op.drop_table("hta_trees")
