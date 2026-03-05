class Service {
  run() {}
}

export class Controller {
  constructor() {
    this.svc = new Service();
  }

  handle() {
    this.svc.run();
  }
}

