package fixture;

import fixture.services.Service;

public class Sample {
    private Service service;

    public Sample(Service service) {
        this.service = service;
    }

    public void handle() {
        this.service.run();
    }
}
