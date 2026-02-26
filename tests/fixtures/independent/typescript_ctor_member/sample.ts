class Service {
  run() {
    return 1;
  }
}

class Controller {
  constructor(private service: Service) {}

  handle() {
    return this.service.run();
  }
}
