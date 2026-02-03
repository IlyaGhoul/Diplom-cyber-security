import sys
import requests
import threading
import logging
from PyQt6 import QtWidgets, QtCore, QtGui
from loginui import Ui_MainWindow

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


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
        
        logger.info("Инициализация приложения завершена")
    
    def send_data_in_thread(self):
        """Запуск отправки в отдельном потоке"""
        logger.info("Нажата кнопка 'Войти'")
        
        self.pushButton.setEnabled(False)
        self.pushButton.setText("...")
        self.statusLabel.setText("Отправка...")
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=self.send_data_thread)
        thread.daemon = True
        thread.start()
        
        logger.debug("Поток для отправки данных запущен")
    
    def send_data_thread(self):
        """Отправка данных в отдельном потоке"""
        try:
            username = self.lineEdit.text()
            password = self.lineEdit_2.text()
            
            logger.info(f"Начинаю отправку данных на сервер")
            logger.debug(f"Данные для отправки: username={username}, password={'*' * len(password)}")
            
            # Создаем JSON данные
            json_data = {
                "username": username,
                "password": password,
                "client_type": "desktop"
            }
            
            logger.debug(f"JSON данные: {json_data}")
            logger.debug(f"URL: http://localhost:8000/api/auth/login")
            
            response = requests.post(
                "http://localhost:8000/api/auth/login",
                json=json_data,
                timeout=3
            )
            
            logger.info(f"Ответ получен. Статус код: {response.status_code}")
            logger.debug(f"Заголовки ответа: {dict(response.headers)}")
            logger.debug(f"Текст ответа: {response.text}")
            
            # Пытаемся распарсить JSON
            try:
                response_json = response.json()
                logger.debug(f"Распарсенный JSON: {response_json}")
                
                success = response_json.get("success", False)
                message = response_json.get("message", "Сообщение отсутствует")
                
                logger.info(f"Успешность авторизации: {success}")
                logger.info(f"Сообщение от сервера: {message}")
                
                # Обновляем UI из главного потока
                QtCore.QMetaObject.invokeMethod(
                    self,
                    "update_ui_after_send",
                    QtCore.Qt.ConnectionType.QueuedConnection,
                    QtCore.Q_ARG(bool, success)
                )
                
            except ValueError as e:
                logger.error(f"Ошибка парсинга JSON: {e}")
                logger.error(f"Ответ не является JSON: {response.text}")
                
                QtCore.QMetaObject.invokeMethod(
                    self,
                    "update_ui_error",
                    QtCore.Qt.ConnectionType.QueuedConnection,
                    QtCore.Q_ARG(str, f"Некорректный ответ сервера: {response.text[:50]}")
                )
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Ошибка подключения к серверу: {e}")
            QtCore.QMetaObject.invokeMethod(
                self,
                "update_ui_error",
                QtCore.Qt.ConnectionType.QueuedConnection,
                QtCore.Q_ARG(str, f"Не удалось подключиться к серверу")
            )
            
        except requests.exceptions.Timeout as e:
            logger.error(f"Таймаут подключения: {e}")
            QtCore.QMetaObject.invokeMethod(
                self,
                "update_ui_error",
                QtCore.Qt.ConnectionType.QueuedConnection,
                QtCore.Q_ARG(str, "Сервер не отвечает (таймаут)")
            )
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запроса: {e}")
            QtCore.QMetaObject.invokeMethod(
                self,
                "update_ui_error",
                QtCore.Qt.ConnectionType.QueuedConnection,
                QtCore.Q_ARG(str, f"Ошибка запроса: {str(e)[:50]}")
            )
            
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
            # Ошибка соединения
            QtCore.QMetaObject.invokeMethod(
                self,
                "update_ui_error",
                QtCore.Qt.ConnectionType.QueuedConnection,
                QtCore.Q_ARG(str, f"Ошибка: {str(e)[:50]}")
            )
    
    @QtCore.pyqtSlot(bool)
    def update_ui_after_send(self, success):
        """Обновить UI после успешной отправки"""
        logger.info(f"Обновление UI. Успех: {success}")
        
        if success:
            self.statusLabel.setText("✅ Авторизация успешна")
            self.pushButton.setText("✅")
            logger.info("Авторизация успешна - обновлено UI")
        else:
            self.statusLabel.setText("❌ Ошибка авторизации")
            self.pushButton.setText("❌")
            logger.warning("Авторизация не удалась - обновлено UI")
        
        # Восстанавливаем через 2 секунды
        QtCore.QTimer.singleShot(2000, self.reset_ui)
        logger.debug("Таймер для сброса UI установлен на 2 секунды")
    
    @QtCore.pyqtSlot(str)
    def update_ui_error(self, error_msg):
        """Обновить UI при ошибке"""
        logger.error(f"Обновление UI с ошибкой: {error_msg}")
        self.statusLabel.setText(f"❌ Ошибка: {error_msg[:30]}")
        self.pushButton.setText("❌")
        QtCore.QTimer.singleShot(2000, self.reset_ui)
    
    def reset_ui(self):
        """Вернуть UI в исходное состояние"""
        logger.info("Сброс UI в исходное состояние")
        self.pushButton.setEnabled(True)
        self.pushButton.setText("Войти")
        self.statusLabel.setText("Готов к отправке")


if __name__ == "__main__":
    # Добавляем обработку Ctrl+C для Poetry
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    logger.info("Запуск приложения PyQt")
    
    app = QtWidgets.QApplication(sys.argv)
    window = SimpleAuthSender()
    window.show()
    
    logger.info("Окно приложения показано")
    
    # Запускаем с обработкой исключений
    try:
        exit_code = app.exec()
        logger.info(f"Приложение завершено с кодом: {exit_code}")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Приложение закрыто по Ctrl+C")
    except Exception as e:
        logger.error(f"Критическая ошибка приложения: {e}", exc_info=True)
        print(f"Ошибка: {e}")