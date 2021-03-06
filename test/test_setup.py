import unittest
from subprocess import CalledProcessError

from mock import patch, Mock

import resources.collectd_outputs as resources
import src.setup as installer
from helpers.output_catcher import output_catcher
from src.setup import Command, get_collectd_info, CollectdInfo


class CollectdInfoTest(unittest.TestCase):

    def test_collectd_info_extracts_from_redhat_version(self):
        self.assert_with_sample(resources.SAMPLE1)

    def test_collectd_info_extracts_from_ubuntu_version(self):
        self.assert_with_sample(resources.SAMPLE2)

    def test_collectd_info_extracts_from_compiled_version(self):
        self.assert_with_sample(resources.SAMPLE3)

    def test_collectd_info_extracts_alphanumeric_version_number(self):
        self.assert_with_sample(resources.SAMPLE4)

    @patch("src.setup.check_output")
    @patch("src.setup.path")
    def test_helper_checks_system_path_first(self, path_mock, check_output_mock):
        check_output_mock.side_effect = [resources.SAMPLE1[resources.COLLECTD_PATH_KEY], resources.SAMPLE1[resources.OUTPUT_KEY]]
        path_mock.exists.return_value = True
        collectd_info = get_collectd_info()
        self.assertEqual(resources.SAMPLE1[resources.COLLECTD_PATH_KEY], collectd_info.exec_path)

    @patch("src.setup.check_output")
    @patch("src.setup.path")
    def test_helper_checks_compilation_path_second(self, path_mock, check_output_mock):
        check_output_mock.side_effect = [CalledProcessError(1, installer.FIND_COMMAND.format("collectd"), None), resources.SAMPLE1[resources.OUTPUT_KEY]]
        path_mock.exists.return_value = True
        collectd_info = get_collectd_info()
        self.assertEqual(CollectdInfo.DEFAULT_COMPILE_PATH, collectd_info.exec_path)

    @patch("src.setup.check_output")
    @patch("src.setup.path")
    def test_factory_raises_when_collectd_is_not_detected(self, path_mock, check_output_mock):
        check_output_mock.side_effect = [CalledProcessError(1, installer.FIND_COMMAND.format("collectd"), None), resources.SAMPLE1[resources.OUTPUT_KEY]]
        path_mock.exists.return_value = False
        with self.assertRaises(installer.InstallationFailedException) as e:
            get_collectd_info()
        self.assertEqual("Cannot detect collectd.", str(e.exception))

    def assert_with_sample(self, sample):
        with patch("src.setup.check_output") as check_output_mock:
            check_output_mock.side_effect = [sample[resources.COLLECTD_PATH_KEY], sample[resources.OUTPUT_KEY]]
            collectd_info = get_collectd_info()
            self.assertEqual(sample[resources.COLLECTD_PATH_KEY], collectd_info.exec_path)
            self.assertEqual(sample[resources.VERSION_KEY], collectd_info.version)
            self.assertEqual(sample[resources.CONFIG_PATH_KEY], collectd_info.config_path)
            self.assertEqual(sample[resources.SUPPORTED], collectd_info.is_supported_version())
            self.assertEqual(sample[resources.RECOMMENDED], collectd_info.is_recommended_version())


class CommandTest(unittest.TestCase):
    INVALID_COMMAND = "invalid_cmd"
    TEST_MSG = "test message"

    def test_output_of_valid_command(self):
        with output_catcher() as (out, err):
            command = Command("echo test", self.TEST_MSG)
            command.run()
            output = out.getvalue().strip()
            self.assertEquals(self.TEST_MSG + " " + command.OK, output)
            self.assertEquals("test", command.stdout)
            self.assertTrue(command.was_successful)

    def test_output_of_failed_command(self):
        with output_catcher() as (out, err):
            command = Command("which " + self.INVALID_COMMAND, self.TEST_MSG)
            command.run()
            output = out.getvalue().strip()
            self.assertEquals(self.TEST_MSG + " " + command.NOT_OK, output)
            self.assertFalse(command.was_successful)

    def test_output_of_invalid_command(self):
        msg = "Checking for invalid command."
        command = Command(self.INVALID_COMMAND, msg)
        command.run()
        self.assertFalse(command.was_successful)
        self.assertEqual(Command.INVALID_COMMAND_ERROR_MSG.format(command=self.INVALID_COMMAND), command.stderr)
        self.assertEqual("", command.stdout)

    def test_required_command_exits_on_failure(self):
        with self.assertRaises(installer.InstallationFailedException):
            Command(self.INVALID_COMMAND, "", exit_on_failure=True).run()
        with self.assertRaises(installer.InstallationFailedException):
            Command("which " + self.INVALID_COMMAND, "", exit_on_failure=True).run()


class InstallationTest(unittest.TestCase):
    PYTHON_MODULES = ["invalid_module1", "invalid_module2"]

    @patch("src.setup.Command")
    def test_install_python_packages_uses_pip_first(self, command_mock):
        installer.detect_pip = Mock()
        installer.detect_pip.return_value = "pip"
        command_mock.return_value = Mock()
        installer.install_python_packages(self.PYTHON_MODULES)
        command_mock.assert_called_with("pip install --quiet --upgrade --force-reinstall " + " ".join(self.PYTHON_MODULES), 'Installing python dependencies', exit_on_failure=True)

    @patch("src.setup.Command")
    def test_install_python_packages_uses_easy_install_when_pip_is_not_available(self, command_mock):
        installer.detect_pip = Mock()
        installer.detect_pip.side_effect = CalledProcessError(cmd="which python-pip", returncode=1)
        command_mock.return_value = Mock()
        installer.install_python_packages(self.PYTHON_MODULES)
        command_mock.assert_called_with("easy_install -U --quiet " + " ".join(self.PYTHON_MODULES), "Installing python dependencies", exit_on_failure=True)


class ColorTest(unittest.TestCase):
    END = "\033[0m"

    def color_methods_appends_color_end(self):
        test_string = "test"
        self.assertEquals(installer.Color.RED + test_string + self.END, installer.Color.red(test_string))
        self.assertEquals(installer.Color.GREEN + test_string + self.END, installer.Color.green(test_string))
        self.assertEquals(installer.Color.YELLOW + test_string + self.END, installer.Color.yellow(test_string))
        self.assertEquals(installer.Color.CYAN + test_string + self.END, installer.Color.cyan(test_string))

