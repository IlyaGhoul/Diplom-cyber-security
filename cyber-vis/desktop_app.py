import sys
import requests
import threading
from PyQt6 import QtWidgets, QtCore, QtGui
from loginui import Ui_MainWindow


class SimpleAuthSender(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        
        # Настройка полей ввода
        self.lineEdit.setText("ilya")  # Логин
        self.lineEdit_2.setText("1111")  # Пароль
        self.lineEdit_2.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        
        # Настройка кнопок
        self.pushButton.clicked.connect(self.send_data_in_thread)  # Кнопка "Войти"
        self.pushButton_2.clicked.connect(self.close)  # Кнопка "Выйти"
        
        # Создаем статусный лейбл
        self.statusLabel = QtWidgets.QLabel("Готов к отправке", parent=self.centralwidget)
        self.statusLabel.setGeometry(QtCore.QRect(170, 530, 471, 30))
        self.statusLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        
        self.setWindowTitle("Auth Sender")
        
        # Блокируем изменение размера окна
        self.setFixedSize(self.size())
    
    def send_data_in_thread(self):
        """Запуск отправки в отдельном потоке"""
        self.pushButton.setEnabled(False)
        self.pushButton.setText("...")
        self.statusLabel.setText("Отправка...")
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=self.send_data_thread)
        thread.daemon = True
        thread.start()
    
    def send_data_thread(self):
        """Отправка данных в отдельном потоке"""
        try:
            response = requests.post(
                "http://localhost:8000/api/auth/login",
                json={
                    "username": self.lineEdit.text(),
                    "password": self.lineEdit_2.text(),
                    "client_type": "desktop"
                },
                timeout=3
            )
            
            success = response.json().get("success", False)
            
            # Обновляем UI из главного потока
            QtCore.QMetaObject.invokeMethod(
                self,
                "update_ui_after_send",
                QtCore.Qt.ConnectionType.QueuedConnection,
                QtCore.Q_ARG(bool, success)
            )
            
        except Exception as e:
            # Ошибка соединения
            QtCore.QMetaObject.invokeMethod(
                self,
                "update_ui_error",
                QtCore.Qt.ConnectionType.QueuedConnection,
                QtCore.Q_ARG(str, str(e))
            )
    
    @QtCore.pyqtSlot(bool)
    def update_ui_after_send(self, success):
        """Обновить UI после успешной отправки"""
        if success:
            self.statusLabel.setText("✅ Авторизация успешна")
            self.pushButton.setText("✅")
        else:
            self.statusLabel.setText("❌ Ошибка авторизации")
            self.pushButton.setText("❌")
        
        # Восстанавливаем через 2 секунды
        QtCore.QTimer.singleShot(2000, self.reset_ui)
    
    @QtCore.pyqtSlot(str)
    def update_ui_error(self, error_msg):
        """Обновить UI при ошибке"""
        self.statusLabel.setText(f"❌ Ошибка: {error_msg[:30]}")
        self.pushButton.setText("❌")
        QtCore.QTimer.singleShot(2000, self.reset_ui)
    
    def reset_ui(self):
        """Вернуть UI в исходное состояние"""
        self.pushButton.setEnabled(True)
        self.pushButton.setText("Войти")
        self.statusLabel.setText("Готов к отправке")


if __name__ == "__main__":
    # Добавляем обработку Ctrl+C для Poetry
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    app = QtWidgets.QApplication(sys.argv)
    window = SimpleAuthSender()
    window.show()
    
    # Запускаем с обработкой исключений
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("\nПриложение закрыто")
    except Exception as e:
        print(f"Ошибка: {e}")