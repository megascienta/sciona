package fixture.sample;

class Service {
  int run() {
    return 1;
  }
}

public class Sample {
  private final Service service;

  public Sample(Service service) {
    this.service = service;
  }

  public int handle() {
    return this.service.run();
  }
}
