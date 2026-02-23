import * as svc from "./services";

export class Controller {
  constructor() {
    this.client = svc;
  }

  handle() {
    this.client.run();
    svc.run();
  }
}
