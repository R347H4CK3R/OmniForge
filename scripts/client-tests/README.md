# Native readiness policy checks

Run from the repository root. These do not contact a host or read saved credentials.

Android's regular `testDebugUnitTest` task includes `ProjectDashboardTest` (URL safety and bounded response reads). For a standalone JDK check without the Android SDK:

```
javac -d /tmp/omniforge-readiness android/app/src/main/java/com/r347h4ck3r/omniforge/ProjectDashboardPolicy.java android/client-tests/ProjectDashboardPolicyCheck.java
java -cp /tmp/omniforge-readiness ProjectDashboardPolicyCheck
javac -d /tmp/omniforge-readiness android/app/src/main/java/com/r347h4ck3r/omniforge/ProjectRequestLifecycle.java android/client-tests/ProjectRequestLifecycleCheck.java
java -cp /tmp/omniforge-readiness ProjectRequestLifecycleCheck
```

On a Mac with Swift installed:

```
swiftc App/ProjectReadiness.swift scripts/client-tests/ios/main.swift -o /tmp/omniforge-readiness-swift
/tmp/omniforge-readiness-swift
```

The Swift check covers prefix preservation, unsafe addresses, empty reports, unsupported schemas, missing fields and oversized reports. Native app compilation is still required; these are not device interaction tests.

Manual device follow-up: saved valid credentials; missing and rejected token; empty and partial report; unreachable host; redirected URL; repeated refresh; navigate away mid-request; background/resume; change endpoint then return. Refresh must never start a build or show the previous request's data after cancellation. Queue statuses are stored metadata, not live worker/build verification.

The isolated request lifecycle harness checks expired queued work, interrupted workers, late connection attachment, repeated cancellation, completion versus a late timer, and isolation between old and new request cancellation. Device-level network/navigation races still need instrumentation or manual verification.
