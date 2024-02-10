import os
import configparser
import shutil
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QPlainTextEdit, QMessageBox
import subprocess


def show_transfer_complete_message():
    QMessageBox.information(None, "交错战线Mod传输工具", "文件传输完成！", QMessageBox.Ok)


def process_files(target_program_path, port_number, file_paths):
    # 切换到目标程序路径（假设adb.exe位于该目录下）
    os.chdir(target_program_path)

    # 指定临时文件夹路径
    temp_folder = "D:\\crosscore-temp"

    # 创建临时文件夹
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)

    try:
        # 将所有文件复制到临时文件夹，并获取新路径列表
        copied_file_paths = []
        for file_path in file_paths:
            # 获取文件的基本名称（不含路径）
            filename = os.path.basename(file_path)
            new_file_path = os.path.join(temp_folder, filename)

            # 复制文件到临时文件夹，保留原有文件名
            shutil.copy2(file_path, new_file_path)
            copied_file_paths.append(new_file_path)

        # 连接到ADB服务器
        # 使用 creationflags 创建无窗口进程
        adb_connect_command = ["adb", "connect", f"127.0.0.1:{port_number}"]
        result = subprocess.run(adb_connect_command, capture_output=True, text=True, encoding='utf-8',
                                creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode != 0:
            print(f"Failed to connect to ADB: {result.stderr}")
            return
        print("success connect to ADB")

        # 将临时文件夹中的文件推送到设备
        for new_file_path in copied_file_paths:
            push_command = ["adb", "push", new_file_path,
                            "/storage/emulated/0/Android/data/com.megagame.crosscore/files/Custom"]
            result = subprocess.run(push_command, capture_output=True, text=True, encoding='utf-8',
                                    creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode != 0:
                print(f"Failed to push file '{new_file_path}' to device: {result.stderr}")

        # 完成传输后删除临时文件夹及其内容
        shutil.rmtree(temp_folder)
        print("mod transfer success")
        show_transfer_complete_message()

    except Exception as e:
        print(f"An error occurred during file processing: {e}")
        # 如果有异常发生，尝试删除临时文件夹
        try:
            shutil.rmtree(temp_folder)
        except Exception:
            pass

class FileDropArea(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setStyleSheet("border: 2px dashed grey;")
        self.text_area = ""

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = [u.toLocalFile() for u in event.mimeData().urls()]
        unique_urls = [url for url in urls if url not in self.parent().files_dropped]
        self.parent().files_dropped.extend(unique_urls)

        # 更新文本区域内容，仅显示当前有效的文件记录
        self.text_area = ""
        for url in self.parent().files_dropped:
            self.text_area += os.path.basename(url) + "\n"
        self.setPlainText(self.text_area)

        event.accept()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("交错战线Mod传输工具")
        self.setGeometry(100, 100, 400, 300)

        self.target_path_label = QLabel("MuMuPlayer-12.0\shell的路径:")
        self.target_path_entry = QLineEdit()

        self.port_label = QLabel("MuMu模拟器adb端口号[默认为16384]:")
        self.port_entry = QLineEdit()

        self.file_label = QLabel("请拖入mod文件[请勿修改文件名，原理为同名文件覆盖]:")
        self.file_drop_area = FileDropArea(self)
        self.files_dropped = []

        self.clear_button = QPushButton("清空文件记录", clicked=self.clear_file_records)

        # 设置默认端口号
        self.default_port_number = 16384
        self.port_entry.setText(str(self.default_port_number))

        # 加载上次保存的配置
        self.load_settings()

        # 如果配置文件中有端口号，则更新输入框中的值
        if 'port_number' in self.config['main']:
            self.port_entry.setText(str(self.config['main']['port_number']))

        self.start_button = QPushButton("确认传输", clicked=self.start_processing)

        layout = QVBoxLayout()
        layout.addWidget(self.target_path_label)
        layout.addWidget(self.target_path_entry)
        layout.addWidget(self.port_label)
        layout.addWidget(self.port_entry)
        layout.addWidget(self.file_label)
        layout.addWidget(self.file_drop_area)
        layout.addWidget(self.clear_button)
        layout.addWidget(self.start_button)

        self.setLayout(layout)

    def start_processing(self):
        target_program = self.target_path_entry.text().strip()
        port_num = self.port_entry.text().strip()

        # 调用业务处理逻辑函数
        process_files(target_program, int(port_num), self.files_dropped)
        # 传输完成后清空文件记录
        self.clear_file_records()

    def clear_file_records(self):
        self.files_dropped.clear()
        self.file_drop_area.setPlainText("")

    def closeEvent(self, event):
        # 保存当前设置
        self.save_settings()

    def load_settings(self):
        self.config = configparser.ConfigParser()

        # 检查settings.ini是否存在，如果不存在则创建一个新文件
        settings_file_path = 'settings.ini'
        if not os.path.exists(settings_file_path):
            with open(settings_file_path, 'w') as configfile:
                self.config.add_section('main')
                self.config.write(configfile)

        self.config.read('settings.ini')

        if 'main' in self.config and 'target_path' in self.config['main']:
            self.target_path_entry.setText(self.config['main']['target_path'])

    def save_settings(self):
        config = configparser.ConfigParser()
        config['main'] = {'target_path': self.target_path_entry.text(), 'port_number': self.port_entry.text()}
        with open('settings.ini', 'w') as configfile:
            config.write(configfile)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()