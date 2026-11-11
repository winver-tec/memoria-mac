// Rotação dos coolers do Mac (AppleSMC, sem sudo). Saída JSON: {"fans":[{"rpm":..,"min":..,"max":..}]}
#include <IOKit/IOKitLib.h>
#include <stdio.h>
#include <string.h>
typedef struct { unsigned char major, minor, build, reserved; unsigned short release; } V;
typedef struct { unsigned short version, length; unsigned int cpuPLimit, gpuPLimit, memPLimit; } L;
typedef struct { unsigned int dataSize, dataType; unsigned char dataAttributes; } I;
typedef struct { unsigned int key; V vers; L pLimitData; I keyInfo; unsigned char result, status, data8; unsigned int data32; unsigned char bytes[32]; } K;
static io_connect_t c;
static unsigned int k4(const char*s){return (s[0]<<24)|(s[1]<<16)|(s[2]<<8)|s[3];}
static int rd(const char*key, K*o){K in; size_t sz=sizeof(K); memset(&in,0,sizeof in); memset(o,0,sizeof *o);
 in.key=k4(key); in.data8=9; if(IOConnectCallStructMethod(c,2,&in,sizeof in,o,&sz))return -1;
 in.keyInfo.dataSize=o->keyInfo.dataSize; in.keyInfo.dataType=o->keyInfo.dataType; in.data8=5;
 unsigned int t=o->keyInfo.dataType; unsigned int n=o->keyInfo.dataSize; memset(o,0,sizeof *o); sz=sizeof(K);
 if(IOConnectCallStructMethod(c,2,&in,sizeof in,o,&sz))return -1; o->keyInfo.dataType=t; o->keyInfo.dataSize=n; return 0;}
static double val(const char*key){K o; if(rd(key,&o))return -1; unsigned int t=o.keyInfo.dataType;
 if(t==k4("flt ")){float f; memcpy(&f,o.bytes,4); return f;}
 if(t==k4("fpe2")) return ((o.bytes[0]<<8)|o.bytes[1])/4.0;
 if(t==k4("ui8 ")) return o.bytes[0];
 return -1;}
int main(){io_service_t s=IOServiceGetMatchingService(kIOMainPortDefault,IOServiceMatching("AppleSMC"));
 if(!s||IOServiceOpen(s,mach_task_self(),0,&c)){printf("{\"fans\":[]}\n");return 0;}
 int n=(int)val("FNum"); if(n<0)n=0; printf("{\"fans\":[");
 for(int i=0;i<n;i++){char a[5],b[5],m[5]; snprintf(a,5,"F%dAc",i); snprintf(b,5,"F%dMn",i); snprintf(m,5,"F%dMx",i);
  printf("%s{\"rpm\":%.0f,\"min\":%.0f,\"max\":%.0f}",i?",":"",val(a),val(b),val(m));}
 printf("]}\n"); IOServiceClose(c); return 0;}
