import type { FakeService } from "./fake-backend"

// The fakes of the project's own services, which `fakeBackend` serves in every test, each built
// fresh for the test, beside the framework's `FakeUsers`. A project adds a fake for each of its
// services here.
export const FAKE_SERVICES: (new () => FakeService)[] = []
