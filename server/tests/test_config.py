"""Testes da configuração de inicialização do servidor."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from server.config import ServerConfig


class ServerConfigTests(unittest.TestCase):
    def test_load_reads_host_and_port_from_env_file(self):
        """Falha se o arquivo .env deixar de alimentar a configuração do servidor."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text(
                "HOST=0.0.0.0\nPORT=9123\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                config = ServerConfig.load(env_file)

        self.assertEqual(config.host, "0.0.0.0")
        self.assertEqual(config.port, 9123)


if __name__ == "__main__":
    unittest.main()
