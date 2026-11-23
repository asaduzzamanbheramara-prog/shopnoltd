from sqlalchemy.dialects import postgresql

from app.models.models import PaymentMethod, Transaction, TxStatus, TxType


def test_transaction_enums_match_existing_varchar_schema():
    # Existing payment migrations define these columns as VARCHAR.
    # Native PostgreSQL enums would require types that the migrations never create.
    expected = {
        "type": (TxType, 16),
        "method": (PaymentMethod, 16),
        "status": (TxStatus, 24),
    }

    for column_name, (enum_class, expected_length) in expected.items():
        column_type = Transaction.__table__.c[column_name].type
        assert column_type.native_enum is False
        assert column_type.length == expected_length
        assert column_type.compile(dialect=postgresql.dialect()) == f"VARCHAR({expected_length})"
        assert set(column_type.enums) == {member.name for member in enum_class}
        assert max(len(member.value) for member in enum_class) <= expected_length
