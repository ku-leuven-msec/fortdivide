#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdio.h>
#include <errno.h>
#include <unistd.h>
#include <string.h>

#include "definitions.h"


struct shm_t* shm_ptr;


unsigned long encrypt_id (unsigned long input)
{
    return input ^ ENCRYPTION_KEY;
}


unsigned long decrypt_id (unsigned long input)
{
    return input ^ ENCRYPTION_KEY;
}


void example()
{
    unsigned long user_id = 0x1122334455667788;
    char message[MVEE_BUFFER_SIZE];

    // wait for external to do its thing
    printf(" > Waiting on external.\n");
    if (sem_wait(&shm_ptr->sem) == -1)
    {
        printf(" > MVEE protected part could not wait on semaphore. - errno: %d\n", errno);
        return;
    }

    user_id = encrypt_id(1000);
    unsigned long messgage_length = shm_ptr->message_length;
    for (size_t message_i = 0; message_i < messgage_length; message_i++)
        message[message_i] = shm_ptr->message[message_i];
    
    char* const env[] = { "bash", nullptr };
    if (!setuid((uid_t) decrypt_id(user_id)))
        execve("/usr/bin/bash", env, nullptr);
    else
        printf(" > could not set uid to %lu\n", decrypt_id(user_id));
}

int main ()
{
    // set up shared memory
    // https://man7.org/linux/man-pages/man3/shm_open.3.html
    int shm_fd = shm_open(MVEE_SHM_NAME, O_CREAT | O_RDWR, S_IRUSR | S_IWUSR);
    if (shm_fd == -1)
    {
        printf(" > MVEE protected part could not acquire shared memory fd. - errno: %d\n", errno);
        return errno;
    }

    if (ftruncate(shm_fd, sizeof(struct shm_t)) == -1)
    {
        printf(" > MVEE protected part could not truncate shared memory. - errno: %d\n", errno);
        return errno;
    }

    shm_ptr = (struct shm_t*) 
            mmap(nullptr, sizeof(struct shm_t), PROT_READ | PROT_WRITE, MAP_SHARED, shm_fd, 0);
    if (shm_ptr == MAP_FAILED)
    {
        printf(" > MVEE protected part could not mmap shared memory. - errno: %d\n", errno);
        return errno;
    }
    memset(shm_ptr->message, 0, MVEE_SHM_MESSAGE_SIZE);
    shm_ptr->message_length = MVEE_BUFFER_SIZE;
    if (sem_init(&shm_ptr->sem, 1, 0) == -1)
    {
        printf(" > MVEE protected part could not set up semaphore 1. - errno: %d\n", errno);
        return errno;
    }

    example();

    // clean up shared memory
    shm_unlink(MVEE_SHM_NAME);
    munmap(shm_ptr, sizeof(struct shm_t));


    printf(" > MVEE protexted part finished. \n");
    return 0;
}