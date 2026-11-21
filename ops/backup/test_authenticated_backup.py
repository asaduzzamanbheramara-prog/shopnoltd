import tempfile
import unittest
from pathlib import Path
from authenticated_backup import create, verify

class AuthenticatedBackupTests(unittest.TestCase):
    def test_round_trip_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'snapshot.enc'
            path.write_bytes(b'Salted__12345678encrypted-payload')
            create(path, 'test-backup-key')
            verify(path, 'test-backup-key')
            path.write_bytes(path.read_bytes()[:-1] + b'X')
            with self.assertRaises(SystemExit):
                verify(path, 'test-backup-key')

    def test_wrong_key_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'snapshot.enc'
            path.write_bytes(b'Salted__12345678encrypted-payload')
            create(path, 'right-key')
            with self.assertRaises(SystemExit):
                verify(path, 'wrong-key')

if __name__ == '__main__':
    unittest.main()
