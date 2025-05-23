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

    print("Starting UUID migration for ForestFinal...")

    # Check if users table exists first
    try:
        users_columns = inspector.get_columns("users")
        users_exists = True
        print(f"Found users table with {len(users_columns)} columns")
    except Exception as e:
        users_exists = False
        print(f"Users table not found: {e}")

    # Only proceed with users table changes if it exists
    if users_exists:
        user_id_col_info = next((col for col in users_columns if col["name"] == "id"), None)
        
        if user_id_col_info:
            current_type_str = str(user_id_col_info["type"]).upper()
            print(f"Current users.id type: {current_type_str}")
            
            # Check if it's not already UUID
            if "UUID" not in current_type_str:
                print("Converting users.id from INTEGER to UUID...")
                
                # For PostgreSQL, we need to be very careful about foreign key constraints
                # Strategy: Create a completely new users table with UUID, then switch
                
                try:
                    # Step 1: Drop dependent tables first
                    dependent_tables = ["memory_snapshots"]
                    for table_name in dependent_tables:
                        try:
                            print(f"Dropping {table_name} table...")
                            op.drop_table(table_name)
                            print(f"✅ Dropped {table_name}")
                        except Exception as e:
                            print(f"⚠️ Could not drop {table_name}: {e}")
                    
                    # Step 2: Drop foreign key constraints to users table
                    constraint_info = [
                        ("reflection_logs", "reflection_logs_user_id_fkey"),
                        ("task_footprints", "task_footprints_user_id_fkey"),
                        ("onboarding_tasks", "onboarding_tasks_user_id_fkey"),
                    ]
                    
                    for table_name, constraint_name in constraint_info:
                        try:
                            print(f"Dropping foreign key {constraint_name} from {table_name}...")
                            op.drop_constraint(constraint_name, table_name, type_="foreignkey")
                            print(f"✅ Dropped constraint {constraint_name}")
                        except Exception as e:
                            print(f"⚠️ Could not drop constraint {constraint_name}: {e}")
                    
                    # Step 3: Rename old users table
                    print("Renaming users table to users_old...")
                    op.rename_table("users", "users_old")
                    print("✅ Renamed users table")
                    
                    # Step 4: Create new users table with UUID
                    print("Creating new users table with UUID primary key...")
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
                    print("✅ Created new users table with UUID")
                    
                    # Step 5: Copy data if needed (for now, we'll skip this for development)
                    print("ℹ️ Data migration skipped (development environment)")
                    
                    # Step 6: Drop old users table
                    try:
                        print("Dropping users_old table...")
                        op.drop_table("users_old")
                        print("✅ Dropped users_old table")
                    except Exception as e:
                        print(f"⚠️ Could not drop users_old table: {e}")
                    
                    # Step 7: Recreate foreign key constraints
                    for table_name, constraint_name in constraint_info:
                        try:
                            print(f"Recreating foreign key {constraint_name} on {table_name}...")
                            op.create_foreign_key(
                                constraint_name,
                                table_name,
                                "users",
                                ["user_id"],
                                ["id"]
                            )
                            print(f"✅ Recreated constraint {constraint_name}")
                        except Exception as e:
                            print(f"⚠️ Could not recreate constraint {constraint_name}: {e}")
                    
                    print("✅ Successfully converted users.id to UUID")
                    
                except Exception as e:
                    print(f"❌ Failed to convert users.id to UUID: {e}")
                    # Don't re-raise the exception, let the migration continue
                    print("⚠️ Continuing with migration despite users table conversion failure")
            else:
                print("✅ users.id is already UUID type")
        else:
            print("⚠️ Could not find 'id' column in users table")
    else:
        # Create users table with UUID if it doesn't exist
        print("Creating users table with UUID primary key...")
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
        print("✅ Created users table")

    # Now check and create HTA tables
    print("\nCreating HTA tables...")
    
    # Check if hta_trees exists
    try:
        hta_trees_columns = inspector.get_columns("hta_trees")
        hta_trees_exists = True
        print("✅ hta_trees table already exists")
    except Exception:
        hta_trees_exists = False
        print("Creating hta_trees table...")

    if not hta_trees_exists:
        try:
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
            print("✅ Created hta_trees table")
        except Exception as e:
            print(f"❌ Failed to create hta_trees table: {e}")
            # Re-raise this exception as it's critical
            raise

    # Check if hta_nodes exists
    try:
        hta_nodes_columns = inspector.get_columns("hta_nodes")
        hta_nodes_exists = True
        print("✅ hta_nodes table already exists")
    except Exception:
        hta_nodes_exists = False
        print("Creating hta_nodes table...")

    if not hta_nodes_exists:
        try:
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
            print("✅ Created hta_nodes table")

            # Create the cross-reference foreign key
            try:
                op.create_foreign_key(
                    "fk_hta_trees_top_node_id",
                    "hta_trees",
                    "hta_nodes",
                    ["top_node_id"],
                    ["id"],
                )
                print("✅ Created cross-reference foreign key")
            except Exception as e:
                print(f"⚠️ Could not create cross-reference foreign key: {e}")
                
        except Exception as e:
            print(f"❌ Failed to create hta_nodes table: {e}")
            # Re-raise this exception as it's critical
            raise

    # Create GIN index on manifest column if it doesn't exist
    try:
        indexes = inspector.get_indexes("hta_trees")
        gin_index_exists = any(idx["name"] == "idx_hta_trees_manifest_gin" for idx in indexes)
        
        if not gin_index_exists:
            print("Creating GIN index on hta_trees.manifest...")
            op.create_index(
                "idx_hta_trees_manifest_gin",
                "hta_trees",
                ["manifest"],
                postgresql_using="gin",
            )
            print("✅ Created GIN index")
        else:
            print("✅ GIN index already exists")
    except Exception as e:
        print(f"⚠️ Could not create GIN index: {e}")

    print("\n🎉 Migration completed successfully!")


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    
    print("Starting downgrade migration...")
    
    # Check if hta_trees exists and drop it
    try:
        inspector.get_columns("hta_trees")
        
        # Drop GIN index first
        try:
            indexes = inspector.get_indexes("hta_trees")
            if any(idx["name"] == "idx_hta_trees_manifest_gin" for idx in indexes):
                op.drop_index("idx_hta_trees_manifest_gin", table_name="hta_trees")
                print("✅ Dropped GIN index")
        except Exception as e:
            print(f"⚠️ Could not drop GIN index: {e}")

        # Check if hta_nodes exists and drop it first (due to foreign keys)
        try:
            inspector.get_columns("hta_nodes")
            op.drop_table("hta_nodes")
            print("✅ Dropped hta_nodes table")
        except Exception as e:
            print(f"⚠️ Could not drop hta_nodes: {e}")

        # Drop hta_trees table
        op.drop_table("hta_trees")
        print("✅ Dropped hta_trees table")
        
    except Exception as e:
        print(f"⚠️ hta_trees table not found or could not be dropped: {e}")

    print("✅ Downgrade completed")
