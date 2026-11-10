package com.r347h4ck3r.omniforge;

import java.net.URI;
import java.io.Reader;
import java.io.IOException;

/** Dashboard-only transport policy; never changes the saved host address. */
public final class ProjectDashboardPolicy {
    private ProjectDashboardPolicy() {}
    public static URI endpoint(String value) {
        URI base = URI.create(value.trim());
        if (!"https".equals(base.getScheme()) || base.getHost() == null || base.getHost().isEmpty()
                || base.getRawUserInfo() != null || base.getRawQuery() != null || base.getRawFragment() != null) {
            throw new IllegalArgumentException("Use an HTTPS host address without credentials, query or fragment in Settings.");
        }
        String address = base.toASCIIString().replaceAll("/+$", "");
        return URI.create(address + "/v1/projects");
    }
    public static String read(Reader reader, int limit) throws IOException {
        StringBuilder text = new StringBuilder();
        char[] buffer = new char[4096];
        for (;;) {
            int count = reader.read(buffer, 0, Math.min(buffer.length, limit - text.length() + 1));
            if (count < 0) return text.toString();
            if (text.length() + count > limit) throw new IOException("Dashboard response exceeds the size limit.");
            text.append(buffer, 0, count);
        }
    }
}
