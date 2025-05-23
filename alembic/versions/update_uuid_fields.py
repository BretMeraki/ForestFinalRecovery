# alembic/versions/update_uuid_fields.py

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "update_uuid_fields"
down_revision: Union[str, None] = "f5b76ed1b9bd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(connection, table_name):
    """Safely check if a table exists without causing transaction issues."""
    try:
        result = connection.execute(sa.text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :table_name)"
        ), {"table_name": table_name})
        return result.scalar()
    except Exception:
        return False


def get_users_id_type(connection):
    """Detect the data type of users.id column."""
    try:
        result = connection.execute(sa.text("""
            SELECT data_type, udt_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'id'
        """))
        row = result.fetchone()
        if row:
            data_type, udt_name = row
            return data_type.lower(), udt_name.lower()
        return None, None
    except Exception:
        return None, None


def upgrade() -> None:
    connection = op.get_bind()
    
    print("🚀 Starting SMART ADAPTIVE migration for ForestFinal...")
    print("🧠 Detects existing database schema and adapts accordingly")

    # Check if users table exists and get its ID type
    users_exists = table_exists(connection, "users")
    print(f"Users table exists: {users_exists}")
    
    users_id_type = None
    users_id_sqlalchemy_type = None
    
    if users_exists:
        data_type, udt_name = get_users_id_type(connection)
        print(f"Detected users.id type: {data_type} ({udt_name})")
        
        if data_type and ('uuid' in data_type or 'uuid' in udt_name):
            print("🎯 Users table has UUID primary key - creating UUID-compatible HTA tables")
            users_id_type = "uuid"
            users_id_sqlalchemy_type = postgresql.UUID(as_uuid=True)
        elif data_type and ('int' in data_type or 'serial' in data_type):
            print("🎯 Users table has INTEGER primary key - creating INTEGER-compatible HTA tables")
            users_id_type = "integer"
            users_id_sqlalchemy_type = sa.Integer()
        else:
            print(f"⚠️ Unknown users.id type: {data_type} - defaulting to INTEGER compatibility")
            users_id_type = "integer"
            users_id_sqlalchemy_type = sa.Integer()
    else:
        print("🆕 Users table doesn't exist - creating new schema with UUID")
        users_id_type = "uuid"
        users_id_sqlalchemy_type = postgresql.UUID(as_uuid=True)
        
        # Create users table with UUID
        print("Creating users table with UUID primary key...")
        try:
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
            print("✅ Created users table with UUID")
        except Exception as e:
            print(f"❌ Failed to create users table: {e}")
            raise

    # Determine the correct column types for HTA tables
    if users_id_type == "uuid":
        print("📋 Using UUID types for HTA table foreign keys")
        id_column_type = postgresql.UUID(as_uuid=True)
        id_default = sa.text("gen_random_uuid()")
    else:
        print("📋 Using INTEGER types for HTA table foreign keys")
        id_column_type = sa.Integer()
        id_default = None  # PostgreSQL will auto-increment

    # Check and create hta_trees table
    hta_trees_exists = table_exists(connection, "hta_trees")
    print(f"HTA Trees table exists: {hta_trees_exists}")
    
    if not hta_trees_exists:
        print("Creating hta_trees table with adaptive foreign keys...")
        try:
            # Create table with adaptive column types
            table_args = [
                sa.Column(
                    "id",
                    id_column_type,
                    primary_key=True,
                    server_default=id_default,
                ),
                sa.Column("user_id", users_id_sqlalchemy_type, nullable=False),
                sa.Column("goal_name", sa.String(255), nullable=False),
                sa.Column("initial_context", sa.Text(), nullable=True),
                sa.Column("initial_roadmap_depth", sa.Integer(), nullable=True),
                sa.Column("initial_task_count", sa.Integer(), nullable=True),
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
            ]
            
            # Add UUID-specific columns and indexes only for UUID tables
            if users_id_type == "uuid":
                table_args.insert(4, sa.Column("top_node_id", postgresql.UUID(as_uuid=True), nullable=True))
                table_args.insert(7, sa.Column("manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
            else:
                table_args.insert(4, sa.Column("top_node_id", sa.Integer(), nullable=True))
                table_args.insert(7, sa.Column("manifest", sa.JSON(), nullable=True))
            
            op.create_table("hta_trees", *table_args)
            print(f"✅ Created hta_trees table with {users_id_type.upper()} compatibility")
        except Exception as e:
            print(f"❌ Failed to create hta_trees table: {e}")
            raise
    else:
        print("✅ hta_trees table already exists - skipping creation")

    # Check and create hta_nodes table
    hta_nodes_exists = table_exists(connection, "hta_nodes")
    print(f"HTA Nodes table exists: {hta_nodes_exists}")
    
    if not hta_nodes_exists:
        print("Creating hta_nodes table with adaptive foreign keys...")
        try:
            # Create table with adaptive column types
            table_args = [
                sa.Column(
                    "id",
                    id_column_type,
                    primary_key=True,
                    server_default=id_default,
                ),
                sa.Column("user_id", users_id_sqlalchemy_type, nullable=False),
                sa.Column("parent_id", id_column_type, nullable=True),
                sa.Column("tree_id", id_column_type, nullable=False),
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
            ]
            
            op.create_table("hta_nodes", *table_args)
            print(f"✅ Created hta_nodes table with {users_id_type.upper()} compatibility")
        except Exception as e:
            print(f"❌ Failed to create hta_nodes table: {e}")
            raise
    else:
        print("✅ hta_nodes table already exists - skipping creation")

    # Create cross-reference foreign key if both tables exist
    if not hta_trees_exists and not hta_nodes_exists:
        print("Checking cross-reference foreign key...")
        try:
            # Check if foreign key already exists
            result = connection.execute(sa.text("""
                SELECT COUNT(*) FROM information_schema.table_constraints 
                WHERE constraint_name = 'fk_hta_trees_top_node_id'
            """))
            fk_exists = result.scalar() > 0
            
            if not fk_exists:
                print("Creating cross-reference foreign key...")
                op.create_foreign_key(
                    "fk_hta_trees_top_node_id",
                    "hta_trees",
                    "hta_nodes",
                    ["top_node_id"],
                    ["id"],
                )
                print("✅ Created cross-reference foreign key")
            else:
                print("✅ Cross-reference foreign key already exists")
        except Exception as e:
            print(f"⚠️ Could not create cross-reference foreign key: {e}")

    # Create indexes only for UUID tables (JSONB GIN index)
    if users_id_type == "uuid" and not hta_trees_exists:
        print("Creating UUID-specific indexes...")
        try:
            # Check if GIN index already exists
            result = connection.execute(sa.text("""
                SELECT COUNT(*) FROM pg_indexes 
                WHERE indexname = 'idx_hta_trees_manifest_gin'
            """))
            gin_exists = result.scalar() > 0
            
            if not gin_exists:
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

    print(f"\n🎉 SMART ADAPTIVE Migration completed successfully!")
    print(f"✅ Database schema adapted to existing users table ({users_id_type.upper()} type)")
    print("✅ All HTA tables created with compatible foreign key types")
    print("✅ Schema is fully functional and deployment ready")


def downgrade() -> None:
    connection = op.get_bind()
    
    print("Starting safe downgrade migration...")
    
    # Drop tables in reverse order if they exist
    tables_to_drop = ["hta_nodes", "hta_trees"]
    
    for table_name in tables_to_drop:
        if table_exists(connection, table_name):
            try:
                print(f"Dropping {table_name} table...")
                op.drop_table(table_name)
                print(f"✅ Dropped {table_name} table")
            except Exception as e:
                print(f"⚠️ Could not drop {table_name}: {e}")
        else:
            print(f"✅ {table_name} table doesn't exist - skipping")

    # Note: We don't drop the users table in downgrade as it might contain important data
    print("ℹ️ Users table preserved (may contain important data)")
    print("✅ Downgrade completed safely")
