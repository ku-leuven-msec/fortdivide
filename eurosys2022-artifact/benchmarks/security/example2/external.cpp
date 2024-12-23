#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdio.h>
#include <errno.h>
#include <unistd.h>
#include <string.h>

#include "definitions.h"


struct shm_t* shm_ptr = nullptr;


void example()
{
    *(unsigned long*)(&shm_ptr->message[MVEE_BUFFER_SIZE + sizeof(unsigned long)]) = 0 ^ LEAKED_KEY;
    for (int i = 0; i < MVEE_BUFFER_SIZE; i++)
        shm_ptr->message[i] = 0x11;
    shm_ptr->message_length = MVEE_BUFFER_SIZE + 2 * sizeof(unsigned long);

    // notify the mvee protected program
    printf(" > Notifying MVEE protected part.\n");
    if (sem_post(&shm_ptr->sem1) == -1)
    {
        printf(" > External part could not post on semaphore 2. - errno: %d\n", errno);
        return;
    }

    // wait on mvee protected program
    printf(" > Waiting on MVEE protected part.\n");
    if (sem_wait(&shm_ptr->sem2) == -1)
    {
        printf(" > External part could not post on semaphore 2. - errno: %d\n", errno);
        return;
    }

    printf(" > message in shared memory: %s\n", shm_ptr->message);
}


int main()
{    // set up shared memory
    // https://man7.org/linux/man-pages/man3/shm_open.3.html
    int shm_fd = shm_open(MVEE_SHM_NAME, O_RDWR, S_IRUSR | S_IWUSR);
    if (shm_fd == -1)
    {
        printf(" > External part could not acquire shared memory fd. - errno: %d\n", errno);
        return errno;
    }

    shm_ptr = (struct shm_t*) mmap(nullptr, sizeof(struct shm_t), PROT_READ | PROT_WRITE, MAP_SHARED, shm_fd, 0);
    if (shm_ptr == MAP_FAILED)
    {
        printf(" > External part could not mmap shared memory. - errno: %d\n", errno);
        shm_unlink(MVEE_SHM_NAME);
        return errno;
    }

    example();

    // clean up shared memory
    shm_unlink(MVEE_SHM_NAME);
    munmap(shm_ptr, sizeof(struct shm_t));


    printf(" > External part finished. \n");
    return 0;
}