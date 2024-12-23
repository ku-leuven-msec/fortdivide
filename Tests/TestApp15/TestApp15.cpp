#include <stdio.h>
#include <pthread.h>
#include <unistd.h>

#define MAXTHREADS 50

int* nums;

void eat_cpu()
{
    int max = 0x3FFF;
    for (int i = 0; i < max; ++i)
    {
        for (int j = 0; j < max; ++j)
        {
            *(int*)nums = i*j;
        }
    }
}

void* thread_func(void* param)
{
    eat_cpu();
    sleep(2);
    eat_cpu();
    sleep(2);
    eat_cpu();
    sleep(2);
    eat_cpu();
    sleep(2);
    return NULL;
}

int main(int argc, char** argv)
{
    printf("Initializing TestApp15\n");
    int i = 0;
    pthread_t threads[MAXTHREADS];
    nums = new int[MAXTHREADS];

    for (i = 0; i < MAXTHREADS; ++i)
    {
        printf("Creating Thread %d...\n",i);
        nums[i] = i;
        pthread_create( &threads[i], NULL, thread_func, &nums[i] );
    }

    for (i = 0; i < MAXTHREADS; ++i)
    {
        printf("Joining Thread %d...\n",i);
        pthread_join( threads[i], NULL );
    }

    return 0;
}
