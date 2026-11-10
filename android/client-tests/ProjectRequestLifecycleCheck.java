import com.r347h4ck3r.omniforge.ProjectRequestLifecycle;
import java.util.concurrent.atomic.AtomicInteger;

public class ProjectRequestLifecycleCheck {
    private static void check(boolean condition, String why) { if (!condition) throw new AssertionError(why); }
    public static void main(String[] args) {
        ProjectRequestLifecycle queued = new ProjectRequestLifecycle();
        queued.cancel();
        check(!queued.begin(), "Expired queued work started");
        AtomicInteger earlyDisconnect = new AtomicInteger();
        check(!queued.attach(earlyDisconnect::incrementAndGet), "Expired work attached");
        check(earlyDisconnect.get() == 1, "Late connection was not closed");

        AtomicInteger oldDisconnect = new AtomicInteger(), newDisconnect = new AtomicInteger();
        ProjectRequestLifecycle oldRequest = new ProjectRequestLifecycle();
        ProjectRequestLifecycle newRequest = new ProjectRequestLifecycle();
        check(oldRequest.attach(oldDisconnect::incrementAndGet) && oldRequest.begin(), "Old request did not begin");
        check(newRequest.attach(newDisconnect::incrementAndGet) && newRequest.begin(), "New request did not begin");
        oldRequest.cancel(); oldRequest.cancel();
        check(!oldRequest.finish(), "Cancelled result accepted for rendering");
        check(oldDisconnect.get() == 1, "Old cancellation repeated");
        check(newDisconnect.get() == 0 && newRequest.isActive(), "Old timer cancelled new request");
        check(newRequest.finish(), "Live completion rejected"); newRequest.cancel();
        check(newDisconnect.get() == 0, "Late timer acted after completion");
        check(!newRequest.begin(), "Completed request restarted");

        ProjectRequestLifecycle interrupted = new ProjectRequestLifecycle();
        Thread.currentThread().interrupt();
        check(!interrupted.begin(), "Interrupted worker started request");
        Thread.interrupted();
        System.out.println("Dashboard request lifecycle checks passed");
    }
}
