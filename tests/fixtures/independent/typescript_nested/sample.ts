class Outer {
  static Inner = class Inner {
    ping() {
      helper();
    }
  };
}

function helper() {
  return 1;
}
