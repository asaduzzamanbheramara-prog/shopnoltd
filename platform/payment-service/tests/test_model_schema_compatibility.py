from sqlalchemy.dialects import postgresql

from app.models.models import PaymentMethod, Transaction, TxStatus, TxType


def test_transaction_enums_match_existing_varchar_schema():
    # Existing payment migrations define these columns as VARCHAR(16).
    # Native PostgreSQL enums would require types that the migrations never create.
    expected = {
        "type": TxType,
        "method": PaymentMethod,
        "status": TxStatus,
    }

    for column_name, enum_class in expected.items():
        column_type = Transaction.__table__.c[column_name].type
        assert column_type.native_enum is False
        assert column_type.length == 16
        assert column_type.compile(dialect=postgresql.dialect()) == "VARCHAR(16)"
        assert set(column_type.enums) == {member.name for member in enum_class}
