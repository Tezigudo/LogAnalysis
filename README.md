#Log Analytics


```java
class Example{

    String x = "";

    boolean processA(String x){
        ...
    }

    boolean processB(String x){
        ...
    }

    boolean finalizeProcess(String x){
        ...
    }

    void doSomething(){
        if(processA(x)){
            ... // modifidy x value
        }

        if(processB(x)){
            ... // modifidy x value
        }

        log.info("Process finished", x);
        finalizeProcess(x); // this might cause error
    }
}
```