import { tenantsApiGetConsultant, type UserSchema } from "@/client";
import { createGlobalState } from "@vueuse/core";
import { ref } from "vue";


export const useUsers = createGlobalState(() => {
    const users = ref<UserSchema[]>([])
    const loading = new Map<number, Promise<UserSchema>>();
    
    async function getUser(id: number) {
        if(loading.has(id)) {
            await loading.get(id);
        }
        const existingUser = users.value.find((user) => user.id === id);

        if (existingUser) {
            return existingUser;
        }
        try {
            loading.set(id, tenantsApiGetConsultant({path: {pk: id}}).then(response => {
                if(!response.data) 
                    throw new Error("User not found");
                users.value.push(response.data);
                return response.data;
            }));
            return await loading.get(id)!;
        } catch (error) {
            console.error("Error fetching user:", error);
            throw error;
        }
    }

    return {
        users,
        getUser
    };
});