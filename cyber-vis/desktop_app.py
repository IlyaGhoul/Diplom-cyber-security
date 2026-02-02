import sys
import requests
import threading
from PyQt6 import QtWidgets, QtCore

class SimpleAuthSender(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
        widget = QtWidgets.QWidget()
        self.setCentralWidget(widget)
        layout = QtWidgets.QVBoxLayout(widget)
        
        # Поля ввода
        self.login = QtWidgets.QLineEdit("ilya")
        self.password = QtWidgets.QLineEdit("1111")
        self.password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        
        # Кнопка
        self.btn = QtWidgets.QPushButton("Отправить")
        self.btn.clicked.connect(self.send_data_in_thread)
        
        # Статус
        self.status = QtWidgets.QLabel("Готов к отправке")
        
        # Сборка
        layout.addWidget(QtWidgets.QLabel("Логин:"))
        layout.addWidget(self.login)
        layout.addWidget(QtWidgets.QLabel("Пароль:"))
        layout.addWidget(self.password)
        layout.addWidget(self.btn)
        layout.addWidget(self.status)
        
        self.setWindowTitle("Auth Sender")
        self.setFixedSize(250, 200)
    
    def send_data_in_thread(self):
        """Запуск отправки в отдельном потоке"""
        self.btn.setEnabled(False)
        self.btn.setText("...")
        self.status.setText("Отправка...")
        
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
                    "username": self.login.text(),
                    "password": self.password.text(),
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
            self.status.setText("✅ Отправлено")
            self.btn.setText("✅")
        else:
            self.status.setText("❌ Ошибка авторизации")
            self.btn.setText("❌")
        
        # Восстанавливаем через 2 секунды
        QtCore.QTimer.singleShot(2000, self.reset_ui)
    
    @QtCore.pyqtSlot(str)
    def update_ui_error(self, error_msg):
        """Обновить UI при ошибке"""
        self.status.setText(f"❌ Ошибка: {error_msg[:30]}")
        self.btn.setText("❌")
        QtCore.QTimer.singleShot(2000, self.reset_ui)
    
    def reset_ui(self):
        """Вернуть UI в исходное состояние"""
        self.btn.setEnabled(True)
        self.btn.setText("Отправить")
        self.status.setText("Готов к отправке")

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