import { helper as helperFn } from "./utils";
import * as path from "path";

export class Service {
  run(): void {
    helperFn();
    path.basename("a/b");
  }
}

export function entry(): void {
  const service = new Service();
  service.run();
}
