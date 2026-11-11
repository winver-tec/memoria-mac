#import <Foundation/Foundation.h>
#import <IOKit/hidsystem/IOHIDEventSystemClient.h>
typedef struct __IOHIDEvent *IOHIDEventRef; typedef struct __IOHIDServiceClient *IOHIDServiceClientRef;
IOHIDEventSystemClientRef IOHIDEventSystemClientCreate(CFAllocatorRef);
int IOHIDEventSystemClientSetMatching(IOHIDEventSystemClientRef, CFDictionaryRef);
IOHIDEventRef IOHIDServiceClientCopyEvent(IOHIDServiceClientRef, int64_t, int32_t, int64_t);
CFStringRef IOHIDServiceClientCopyProperty(IOHIDServiceClientRef, CFStringRef);
double IOHIDEventGetFloatValue(IOHIDEventRef, int32_t);
// Temperaturas do Apple Silicon sem sudo (sensores HID da PMU). Saída JSON:
// chip = maior "tdie" (núcleos), ssd = NAND, bateria; estado = thermalState oficial do macOS (0..3).
int main(){@autoreleasepool{ double chip=0,ssd=0,bat=0;
 IOHIDEventSystemClientRef c=IOHIDEventSystemClientCreate(kCFAllocatorDefault);
 IOHIDEventSystemClientSetMatching(c,(__bridge CFDictionaryRef)@{@"PrimaryUsagePage":@0xff00,@"PrimaryUsage":@5});
 NSArray *sv=(__bridge_transfer NSArray*)IOHIDEventSystemClientCopyServices(c);
 for(id s in sv){IOHIDEventRef e=IOHIDServiceClientCopyEvent((__bridge IOHIDServiceClientRef)s,15,0,0); if(!e)continue;
  NSString*n=(__bridge_transfer NSString*)IOHIDServiceClientCopyProperty((__bridge IOHIDServiceClientRef)s,CFSTR("Product"));
  double v=IOHIDEventGetFloatValue(e,15<<16); CFRelease(e); if(v<=0||v>150)continue;
  if([n hasPrefix:@"PMU tdie"]&&v>chip)chip=v; else if([n hasPrefix:@"NAND"]&&v>ssd)ssd=v; else if([n hasPrefix:@"gas gauge"]&&v>bat)bat=v;}
 printf("{\"chip\":%.1f,\"ssd\":%.1f,\"bateria\":%.1f,\"estado\":%ld}\n",chip,ssd,bat,(long)NSProcessInfo.processInfo.thermalState);
}}
