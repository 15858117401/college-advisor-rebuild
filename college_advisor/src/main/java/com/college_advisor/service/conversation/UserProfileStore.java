package com.college_advisor.service.conversation;

public interface UserProfileStore {
    void mergeProfile(String userId, UserProfile extracted);
}
