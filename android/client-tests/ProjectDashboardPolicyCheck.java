import com.r347h4ck3r.omniforge.ProjectDashboardPolicy;
import java.io.StringReader;
public class ProjectDashboardPolicyCheck {
    public static void main(String[] args) throws Exception {
        if (!ProjectDashboardPolicy.endpoint("https://host.test/proxy/android-api/").toString().equals("https://host.test/proxy/android-api/v1/projects")) throw new AssertionError("Proxy prefix lost");
        for (String bad : new String[]{"http://host.test", "https://secret@host.test", "https://host.test/?secret=x", "https://host.test/#x", "https:///empty"}) {
            try { ProjectDashboardPolicy.endpoint(bad); throw new AssertionError("Accepted unsafe endpoint"); } catch (IllegalArgumentException expected) {}
        }
        if (!ProjectDashboardPolicy.read(new StringReader("abc"), 3).equals("abc")) throw new AssertionError("Body changed");
        try { ProjectDashboardPolicy.read(new StringReader("abcd"), 3); throw new AssertionError("Unbounded body"); } catch (java.io.IOException expected) {}
        System.out.println("Dashboard URL and bounded-read checks passed");
    }
}
