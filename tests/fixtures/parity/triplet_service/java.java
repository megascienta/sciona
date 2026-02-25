package parity;

class Service {
  void run() {}
}

class Controller {
  Service svc = new Service();

  void handle() {
    svc.run();
  }
}
